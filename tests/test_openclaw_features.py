"""Application workflows against a fictional OpenClaw server on loopback only."""

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

# Standalone execution must not read the developer's real .env on import.
with patch("dotenv.load_dotenv"):
    from src.agents import worker as gateway_worker
    from src.core.config import Settings
    from src.main import app
    from src.tools import db_queries as db
    from src.validate_live import check
    from src.workflows.chain import build_course


FAKE_TOKEN = "fictional-openclaw-test-token"
SOURCE_TITLE = "Fictional equipment return procedure"
SOURCE_BODY = (
    "Return booking\nBook an equipment return with the training desk before arrival."
    "\n\nReturn evidence\nKeep the desk's return receipt after handing back equipment."
)


def course_content():
    content = build_course(SOURCE_TITLE, SOURCE_BODY)
    content["origin"] = "Fictional gateway-generated draft requiring trainer review"
    return content


@pytest.fixture
def openclaw(tmp_path, monkeypatch):
    state = SimpleNamespace(
        calls=[],
        requested_timeouts=[],
        errors=[],
        status=200,
        reply=lambda payload: json.dumps(course_content()),
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log request headers or model input.

        def do_POST(self):
            try:
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                state.calls.append(
                    {"path": self.path, "headers": self.headers, "payload": payload}
                )
                content = state.reply(payload)
                body = json.dumps(
                    {
                        "choices": [
                            {"finish_reason": "stop", "message": {"content": content}}
                        ]
                    }
                ).encode()
                status = state.status
            except Exception as exc:
                state.errors.append(exc)
                status, body = 500, b'{"error":"fixture failed"}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    state.settings = Settings(
        mode="gateway",
        gateway_protocol="openclaw",
        gateway_url=state.url,
        gateway_api_key=FAKE_TOKEN,
        model="openclaw/agentx-training",
        database_path=tmp_path / "unused-settings.db",
    )

    # Still exercise real HTTP, but reject every destination except this fixture.
    # Disable environment proxies so local requests cannot leave the machine.
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})
    real_open = gateway_worker._open_gateway_request

    def local_only(request, timeout=60):
        target = urlsplit(request.full_url)
        assert (target.scheme, target.hostname, target.port) == (
            "http", "127.0.0.1", server.server_port
        ), "The feature test attempted a non-fixture request"
        state.requested_timeouts.append(timeout)
        return real_open(request, timeout=min(timeout, 2))

    monkeypatch.setattr(gateway_worker, "_open_gateway_request", local_only)
    for name, value in {
        "AGENT_MODE": "gateway",
        "LLM_GATEWAY_PROTOCOL": "openclaw",
        "LLM_GATEWAY_URL": state.url,
        "LLM_GATEWAY_API_KEY": FAKE_TOKEN,
        "LLM_MODEL": "openclaw/agentx-training",
    }.items():
        monkeypatch.setenv(name, value)
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert not state.errors, "The local OpenClaw fixture could not serve a request"


@pytest.fixture
def client(tmp_path, monkeypatch, openclaw):
    monkeypatch.setattr(db, "DB", tmp_path / "openclaw-features.db")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def source_id(client):
    with db.connect() as connection:
        return connection.execute(
            "INSERT INTO documents(title,body,approved,created) VALUES(?,?,1,0)",
            (SOURCE_TITLE, SOURCE_BODY),
        ).lastrowid


def login(client, name="trainer"):
    response = client.post(
        "/api/login", json={"name": name, "password": "LearnDemo2026!"}
    )
    assert response.status_code == 200


def saved_courses():
    with db.connect() as connection:
        return [tuple(row) for row in connection.execute("SELECT * FROM courses ORDER BY id")]


def draft_events():
    with db.connect() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM events WHERE action='draft_course'"
        ).fetchone()[0]


def assert_openclaw_calls(server, expected_count, token_budget, timeout=60):
    assert len(server.calls) == expected_count
    assert server.requested_timeouts == [timeout] * expected_count
    for call in server.calls:
        assert call["path"] == "/v1/chat/completions"
        assert call["headers"]["Authorization"] == "Bearer " + FAKE_TOKEN
        assert call["headers"].get("X-API-Key") is None
        assert not any("session" in name.lower() for name in call["headers"])
        payload = call["payload"]
        assert payload["model"] == "openclaw/agentx-training"
        assert payload["stream"] is False
        assert payload["max_completion_tokens"] == token_budget
        assert not {"user", "tools", "previous_response_id"} & payload.keys()
        assert payload["messages"][0]["role"] == "system"
        assert FAKE_TOKEN not in json.dumps(payload)


def training_reply(payload):
    messages = payload["messages"]
    context = json.loads(messages[1]["content"])
    if "eligible_actions" in context:
        choice = next(a for a in context["eligible_actions"] if a["kind"] == "lesson")
        return json.dumps(
            {
                "tool": "select_approved_activity",
                "args": {
                    "session_id": context["session_id"],
                    "activity_id": choice["activity_id"],
                },
            }
        )
    if len(messages) == 2:
        return json.dumps(
            {"tool": "retrieve_sources", "args": {"query": context["question"]}}
        )
    return json.dumps(
        {"answer": "Ask the supplier for a duplicate receipt. [1]"}
        if "receipt" in context["question"]
        else {"answer": "The approved sources do not answer this; ask your trainer."}
    )


def test_live_validation_runs_all_three_checks_through_real_openclaw_worker(
    openclaw, tmp_path, monkeypatch
):
    untouched = tmp_path / "untouched.db"
    monkeypatch.setattr(db, "DB", untouched)
    openclaw.reply = training_reply

    results = check(openclaw.settings)  # No injected worker: use GatewayWorker and HTTP.

    assert [result["check"] for result in results] == [
        "eligible_activity_without_score_change",
        "approved_policy_citations",
        "unsupported_question_referral",
    ]
    assert all(result["passed"] for result in results)
    assert results[0]["activity_kind"] == "lesson"
    assert results[0]["objective"] == "receipt_evidence"
    assert results[1]["tools"] == results[2]["tools"] == ["retrieve_sources"]
    assert_openclaw_calls(openclaw, expected_count=5, token_budget=512)
    for call in (openclaw.calls[2], openclaw.calls[4]):
        messages = call["payload"]["messages"]
        assert [message["role"] for message in messages] == [
            "system", "user", "assistant", "user"
        ]
        assert json.loads(messages[2]["content"])["tool"] == "retrieve_sources"
        assert "tool_result" in json.loads(messages[3]["content"])
    assert db.DB == untouched
    assert not untouched.exists()


def test_trainer_generates_gateway_course_as_draft(client, source_id, openclaw):
    login(client)
    before = saved_courses()
    events_before = draft_events()

    response = client.post("/api/course/create", json={"document_id": source_id})

    assert response.status_code == 200
    assert_openclaw_calls(openclaw, expected_count=1, token_budget=4096, timeout=180)
    assert len(saved_courses()) == len(before) + 1
    assert saved_courses()[:-1] == before
    assert draft_events() == events_before + 1
    with db.connect() as connection:
        draft = connection.execute(
            "SELECT * FROM courses WHERE document_id=?", (source_id,)
        ).fetchone()
    assert draft["status"] == "draft"
    assert json.loads(draft["content"]) == course_content()
    assert SOURCE_BODY in openclaw.calls[0]["payload"]["messages"][1]["content"]


@pytest.mark.parametrize("actor,status", [(None, 401), ("learner", 403), ("alex", 403)])
def test_course_generation_requires_trainer_before_model_call(
    client, source_id, openclaw, actor, status
):
    if actor:
        login(client, actor)
    before, events_before = saved_courses(), draft_events()

    response = client.post("/api/course/create", json={"document_id": source_id})

    assert response.status_code == status
    assert openclaw.calls == []
    assert saved_courses() == before
    assert draft_events() == events_before


def test_unapproved_source_never_reaches_model(client, source_id, openclaw):
    login(client)
    with db.connect() as connection:
        connection.execute("UPDATE documents SET approved=0 WHERE id=?", (source_id,))
    before, events_before = saved_courses(), draft_events()

    response = client.post("/api/course/create", json={"document_id": source_id})

    assert response.status_code == 400
    assert "Approve the source document first" in response.json()["error"]
    assert openclaw.calls == []
    assert saved_courses() == before
    assert draft_events() == events_before


@pytest.mark.parametrize(
    "failure,status", [("bad_json", 400), ("section_zero", 400), ("section_three", 400), ("http", 503)]
)
def test_failed_gateway_draft_does_not_persist_course_or_success_event(
    client, source_id, openclaw, failure, status
):
    login(client)
    content = course_content()
    if failure == "bad_json":
        openclaw.reply = lambda payload: "not valid course JSON"
    elif failure.startswith("section_"):
        content["lessons"][0]["source_section"] = 0 if failure == "section_zero" else 3
        openclaw.reply = lambda payload: json.dumps(content)
    else:
        openclaw.status = 503
        openclaw.reply = lambda payload: "fictional upstream detail " + FAKE_TOKEN
    before, events_before = saved_courses(), draft_events()

    response = client.post("/api/course/create", json={"document_id": source_id})

    assert response.status_code == status
    assert_openclaw_calls(openclaw, expected_count=1, token_budget=4096, timeout=180)
    assert saved_courses() == before
    assert draft_events() == events_before
    assert FAKE_TOKEN not in response.text
    assert "fictional upstream detail" not in response.text


def test_course_timeout_is_redacted_and_does_not_retry_or_save_draft(
    client, source_id, openclaw, monkeypatch
):
    login(client)
    before, events_before = saved_courses(), draft_events()
    calls = []

    def timeout(request, timeout):
        calls.append((timeout, json.loads(request.data)["max_completion_tokens"]))
        raise TimeoutError("fictional upstream detail " + FAKE_TOKEN)

    monkeypatch.setattr(gateway_worker, "_open_gateway_request", timeout)

    response = client.post("/api/course/create", json={"document_id": source_id})

    assert response.status_code == 503
    assert calls == [(180, 4096)]
    assert openclaw.calls == []
    assert saved_courses() == before
    assert draft_events() == events_before
    assert FAKE_TOKEN not in response.text
    assert "fictional upstream detail" not in response.text
