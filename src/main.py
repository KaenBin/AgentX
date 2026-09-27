"""Web UI and authenticated API entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from src.core.config import ROOT, Settings
from src.core.state import snapshot
from src.tools import db_queries as db
from src.workflows.router import act
from src.agents.orchestrator import TrainingOrchestrator
from src.agents.worker import GatewayError
from src.workflows import readiness
from src.agents.learning_coach import advance
from src.agents.protocol import StrictObject
from pydantic import StrictInt


@asynccontextmanager
async def lifespan(app):
    Settings().validate()
    db.init()
    yield


app = FastAPI(title="AgentX Learn", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "src" / "web"), name="static")


@app.middleware("http")
async def rehearsal_scope(request: Request, call_next):
    import sqlite3
    from src.workflows.rehearsal import lookup
    from src.core.config import MODE_OVERRIDE

    token = request.cookies.get("rehearsal")
    if not token or request.url.path in {"/api/rehearsal/exit", "/api/rehearsal/context"}:
        return await call_next(request)
    try:
        path, mode = lookup(token)
    except (ValueError, OSError, sqlite3.Error):
        return JSONResponse(
            {"error": "Rehearsal is unavailable. Return to the main workspace."},
            status_code=400,
        )
    database_scope = db.DATABASE_OVERRIDE.set(path)
    mode_scope = MODE_OVERRIDE.set(mode)
    try:
        return await call_next(request)
    finally:
        MODE_OVERRIDE.reset(mode_scope)
        db.DATABASE_OVERRIDE.reset(database_scope)


@app.middleware("http")
async def local_guards(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse(
                {"error": "Cross-origin request rejected"}, status_code=403
            )
        # Bound chunked as well as Content-Length requests before JSON parsing.
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 200000:
                return JSONResponse(
                    {"error": "Request exceeds 200 KB"}, status_code=413
                )
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
    )
    return response


@app.exception_handler(ValueError)
async def invalid_request(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=400)


@app.exception_handler(PermissionError)
async def forbidden(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=403)


@app.exception_handler(GatewayError)
async def gateway_failure(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=503)


def authenticated(request: Request):
    user = db.user(request.cookies.get("session", ""))
    if not user:
        raise HTTPException(401, "Please sign in")
    return user


class LoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Enter a question")
        return value.strip()


@app.get("/")
@app.get("/chat", include_in_schema=False)
def index():
    return FileResponse(ROOT / "src" / "web" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "mode": Settings().mode}


@app.post("/api/login")
def login(data: LoginRequest, request: Request):
    token = db.login(data.name, data.password)
    response = JSONResponse({"ok": True})
    response.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="strict",
        max_age=28800,
        secure=request.url.scheme == "https",
    )
    return response


@app.post("/api/logout")
def logout(request: Request, user=Depends(authenticated)):
    db.logout(request.cookies.get("session", ""))
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response


@app.get("/api/state")
def state(user=Depends(authenticated)):
    return snapshot(user) | {"rehearsal": db.DATABASE_OVERRIDE.get() is not None}


class RehearsalRequest(StrictObject):
    mode: str = Field(pattern="^(gateway|demo)$")


@app.get("/api/rehearsal/context")
def rehearsal_context(request: Request):
    from src.workflows.rehearsal import lookup
    import sqlite3

    token = request.cookies.get("rehearsal")
    if not token:
        return {"rehearsal": False}
    try:
        _, mode = lookup(token)
        label = "AI coach" if mode == "gateway" else "Offline simulation"
    except (ValueError, OSError, sqlite3.Error):
        label = "Unavailable — return to main workspace"
    return {"rehearsal": True, "mode": label}


@app.post("/api/rehearsal/start")
def start_rehearsal(
    data: RehearsalRequest, request: Request, user=Depends(authenticated)
):
    from src.workflows.rehearsal import create

    token, session = create(user, data.mode)
    response = JSONResponse({"ok": True})
    options = dict(
        httponly=True,
        samesite="strict",
        max_age=28800,
        secure=request.url.scheme == "https",
    )
    if not request.cookies.get("rehearsal"):
        response.set_cookie(
            "main_session", request.cookies.get("session", ""), **options
        )
    response.set_cookie("rehearsal", token, **options)
    response.set_cookie("session", session, **options)
    return response


@app.post("/api/rehearsal/exit")
def exit_rehearsal(request: Request):
    response = JSONResponse({"ok": True})
    if request.cookies.get("main_session"):
        response.set_cookie(
            "session",
            request.cookies["main_session"],
            httponly=True,
            samesite="strict",
            max_age=28800,
            secure=request.url.scheme == "https",
        )
    else:
        response.delete_cookie("session")
    response.delete_cookie("rehearsal")
    response.delete_cookie("main_session")
    return response


@app.post("/chat")
@app.post("/api/agent")
@app.post("/api/ask")
def chat(data: ChatRequest, user=Depends(authenticated)):
    return TrainingOrchestrator().run(user, data.question)


class LearningStart(StrictObject):
    course_id: StrictInt = Field(gt=0)


class LearningAnswer(StrictObject):
    issued_id: StrictInt = Field(gt=0)
    answer: StrictInt | None = Field(default=None, ge=0)


class ReviewQuestion(StrictObject):
    reason: str = Field(min_length=1, max_length=2000)


class ReviewResolution(StrictObject):
    resolution: str = Field(min_length=1, max_length=2000)


class RevisionDraft(StrictObject):
    old_course_id: StrictInt = Field(gt=0)
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=40, max_length=100000)
    content: dict


class RevisionApproval(StrictObject):
    affected_ids: list[str]
    equivalent_ids: list[str]


@app.post("/api/revisions/draft")
def revision_draft(data: RevisionDraft, user=Depends(authenticated)):
    from src.workflows.change_impact import create

    return create(user, data.old_course_id, data.title, data.body, data.content)


@app.post("/api/revisions/demo")
def revision_demo(data: LearningStart, user=Depends(authenticated)):
    from src.workflows.change_impact import fictional_update

    return fictional_update(user, data.course_id)


@app.post("/api/revisions/{revision_id}/activate")
def revision_activate(
    revision_id: int, data: RevisionApproval, user=Depends(authenticated)
):
    from src.workflows.change_impact import activate

    return activate(user, revision_id, data.affected_ids, data.equivalent_ids)


@app.post("/api/learning/start")
def learning_start(data: LearningStart, user=Depends(authenticated)):
    return readiness.start(user, data.course_id)


@app.get("/api/learning/{sid}")
def learning_state(sid: int, user=Depends(authenticated)):
    return readiness.get(user, sid)


@app.post("/api/learning/{sid}/next")
def learning_next(sid: int, user=Depends(authenticated)):
    return advance(user, sid)


@app.post("/api/learning/{sid}/answer")
def learning_answer(sid: int, data: LearningAnswer, user=Depends(authenticated)):
    return readiness.submit(user, sid, data.issued_id, data.answer)


@app.post("/api/learning/{sid}/review")
def learning_review(sid: int, data: ReviewQuestion, user=Depends(authenticated)):
    return readiness.request_review(user, sid, data.reason)


@app.post("/api/learning/reviews/{review_id}/resolve")
def learning_resolve(
    review_id: int, data: ReviewResolution, user=Depends(authenticated)
):
    return readiness.resolve_review(user, review_id, data.resolution)


@app.post("/api/{action:path}")
def action(action: str, data: dict, user=Depends(authenticated)):
    allowed = {
        "document",
        "document/approve",
        "course/create",
        "course/publish",
        "attempt",
    }
    if action not in allowed:
        raise HTTPException(404, "Unknown action")
    try:
        return act(user, "/api/" + action, data)
    except (KeyError, TypeError) as exc:
        raise HTTPException(400, "Invalid or missing request fields") from exc
