"""Deployment probes and privacy-safe request diagnostics."""

import sqlite3
import time
import asyncio
import json
import re
import traceback

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.tools import db_queries as db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Run the app against a fresh fictional database."""
    monkeypatch.setattr(db, "DB", tmp_path / "main.db")
    with TestClient(app) as client:
        yield client


def test_ready_checks_initialized_database_without_model_calls(client, monkeypatch):
    """Readiness reports the deployed app while liveness keeps its existing shape."""
    def no_model(*args, **kwargs):
        """Fail the probe test if readiness attempts to use the model gateway."""
        raise AssertionError("A readiness probe must not call the gateway")

    monkeypatch.setattr("src.agents.worker.GatewayWorker.chat", no_model)
    assert client.get("/health").json() == {"status": "ok", "mode": "demo"}
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "mode": "demo", "version": "0.3.0"}
    assert app.version == "0.3.0"


@pytest.mark.parametrize("kind", ["missing", "empty", "corrupt", "incomplete"])
def test_ready_rejects_unusable_database_without_creating_or_seeding_it(
    client, tmp_path, monkeypatch, kind
):
    """A probe never repairs, seeds or discloses a failing database."""
    path = tmp_path / "private-path" / "probe.db"
    if kind != "missing":
        path.parent.mkdir()
        if kind == "corrupt":
            path.write_bytes(b"not a SQLite database")
        else:
            path.touch()
            if kind == "incomplete":
                with sqlite3.connect(path) as connection:
                    connection.execute("CREATE TABLE users(id INTEGER PRIMARY KEY)")
    before = path.read_bytes() if path.exists() else None
    monkeypatch.setattr(db, "DB", path)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "error": "Database unavailable"}
    assert str(path) not in response.text
    if before is None:
        assert not path.parent.exists()
    else:
        assert path.read_bytes() == before
    assert client.get("/health").status_code == 200


def test_ready_rejects_missing_learning_table(client):
    """An authentication table alone does not establish learning readiness."""
    with db.connect() as connection:
        connection.execute("DROP TABLE learning_refreshes")
    assert client.get("/ready").status_code == 503


def test_ready_lock_wait_is_bounded_and_recovers(client):
    """A transient exclusive lock returns promptly and a later probe recovers."""
    connection = sqlite3.connect(db.DB)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        assert client.get("/ready").status_code == 503
        assert time.monotonic() - started < 3
    finally:
        connection.rollback()
        connection.close()
    assert client.get("/ready").status_code == 200


def test_ready_ignores_rehearsal_cookie_and_database_override(client, tmp_path):
    """Deployment probes cannot be redirected by a participant's workspace."""
    client.cookies.set("rehearsal", "0" * 32)
    scope = db.DATABASE_OVERRIDE.set(tmp_path / "absent-rehearsal.db")
    try:
        assert client.get("/ready").status_code == 200
    finally:
        db.DATABASE_OVERRIDE.reset(scope)


def request_logs(capfd):
    """Read only the app's structured HTTP records from captured stderr."""
    return [
        json.loads(line) for line in capfd.readouterr().err.splitlines()
        if line.startswith('{"event": "http_request"')
    ]


def test_request_ids_cover_success_auth_validation_and_guard_errors(client, capfd):
    """Every response gets its own ID, including errors before route execution."""
    secret = "private-request-material"
    requests = [
        ("GET", "/health", {}, 200),
        ("GET", "/api/state", {}, 401),
        ("GET", f"/api/learning/8675309?token={secret}", {}, 401),
        ("GET", f"/absent/{secret}?token={secret}", {}, 404),
        ("POST", "/api/login", {"json": {"password": secret}}, 422),
        ("POST", "/api/login", {"headers": {"Origin": f"https://{secret}.test"}}, 403),
        ("POST", "/api/login", {"content": secret * 20000}, 413),
    ]
    ids = set()
    for method, path, options, expected in requests:
        headers = options.pop("headers", {}) | {"X-Request-ID": secret, "Cookie": f"session={secret}"}
        response = client.request(method, path, headers=headers, **options)
        assert response.status_code == expected
        request_id = response.headers.get("X-Request-ID", "")
        assert re.fullmatch(r"[0-9a-f]{32}", request_id)
        ids.add(request_id)
    assert len(ids) == len(requests)
    logs = request_logs(capfd)
    assert len(logs) == len(requests)
    assert {entry["request_id"] for entry in logs} == ids
    assert secret not in json.dumps(logs)
    assert "8675309" not in json.dumps(logs)
    assert any(entry["route"] == "/api/learning/{sid}" for entry in logs)
    assert set(logs[0]) == {
        "event", "timestamp", "level", "request_id", "method", "route",
        "status_code", "duration_ms", "error_kind",
    }


def test_unexpected_error_is_correlated_without_exception_or_request_data(
    client, monkeypatch, capfd
):
    """An unhandled error returns a usable ID while private exception text stays out."""
    secret = "private-password-and-chat-text"

    def broken_user(token):
        """Raise private exception text to exercise the generic error response."""
        raise RuntimeError(secret)

    monkeypatch.setattr(db, "user", broken_user)
    with TestClient(app, raise_server_exceptions=False) as errors:
        response = errors.get(f"/api/state?credential={secret}", headers={"Cookie": f"session={secret}"})
    assert response.status_code == 500
    request_id = response.headers.get("X-Request-ID", "")
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)
    assert response.json() == {"error": "Request failed. Retry or share the request ID.", "request_id": request_id}
    logs = request_logs(capfd)
    assert len(logs) == 1
    assert logs[0]["request_id"] == request_id
    assert logs[0]["status_code"] == 500
    assert logs[0]["route"] == "/api/state"
    assert logs[0]["error_kind"] == "unhandled_exception"
    assert logs[0]["level"] == "ERROR"
    assert secret not in json.dumps(logs)


def test_handled_gateway_failure_has_safe_metadata(client, monkeypatch, capfd):
    """Handled upstream errors use the same request ID and an explicit category."""
    from src.agents.worker import GatewayError

    assert client.post("/api/login", json={"name": "learner", "password": "LearnDemo2026!"}).status_code == 200
    capfd.readouterr()
    secret = "private-question-and-provider-message"

    def unavailable(*args):
        """Simulate a handled gateway failure containing a privacy canary."""
        raise GatewayError(secret)

    monkeypatch.setattr("src.main.TrainingOrchestrator.run", unavailable)
    response = client.post("/api/ask", json={"question": secret})
    assert response.status_code == 503
    logs = request_logs(capfd)
    assert len(logs) == 1
    assert logs[0]["error_kind"] == "gateway_unavailable"
    assert logs[0]["request_id"] == response.headers["X-Request-ID"]
    assert secret not in json.dumps(logs)


def test_ready_failure_logs_category_without_database_path(client, tmp_path, monkeypatch, capfd):
    """Database errors are diagnosable without exposing the configured filesystem."""
    path = tmp_path / "private-db-name.db"
    monkeypatch.setattr(db, "DB", path)
    response = client.get("/ready")
    assert response.status_code == 503
    logs = request_logs(capfd)
    assert len(logs) == 1
    assert logs[0]["error_kind"] == "database_unavailable"
    assert logs[0]["request_id"] == response.headers["X-Request-ID"]
    assert str(path) not in json.dumps(logs)
    assert path.name not in json.dumps(logs)


def test_interrupted_response_reraises_only_a_safe_error(capfd):
    """A started response cannot be replaced; its re-raised error omits private text."""
    from src.utils.logging import RequestDiagnostics

    secret = "private-stream-exception"
    sent = []

    async def broken(scope, receive, send):
        """Start a response before raising an exception with private text."""
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError(secret)

    async def send(message):
        """Collect ASGI response messages for header and interruption assertions."""
        sent.append(message)

    async def receive():
        """Supply an empty ASGI HTTP request to the diagnostic middleware."""
        return {"type": "http.request", "body": b""}

    with pytest.raises(RuntimeError) as error:
        asyncio.run(RequestDiagnostics(broken)(
            {"type": "http", "method": "GET", "path": "/private/path", "headers": []}, receive, send
        ))
    assert secret not in "".join(traceback.format_exception(error.value))
    assert len(sent) == 1
    assert any(name == b"x-request-id" for name, value in sent[0]["headers"])
    logs = request_logs(capfd)
    assert len(logs) == 1
    assert logs[0]["error_kind"] == "response_interrupted"
    assert logs[0]["status_code"] == 200
    assert secret not in json.dumps(logs)


def test_non_http_scope_passes_through_without_request_logging(capfd):
    """Lifespan and websocket protocol events keep their normal behavior."""
    from src.utils.logging import RequestDiagnostics

    scopes = []

    async def downstream(scope, receive, send):
        """Record the unchanged non-HTTP scope received from the middleware."""
        scopes.append(scope)

    async def noop():
        """Provide an unused protocol callback for the lifespan passthrough test."""
        pass

    asyncio.run(RequestDiagnostics(downstream)({"type": "lifespan"}, noop, noop))
    assert scopes == [{"type": "lifespan"}]
    assert request_logs(capfd) == []


def test_ready_uses_main_mode_and_database_during_valid_gateway_rehearsal(
    client, monkeypatch
):
    """A healthy live rehearsal cannot mask an unavailable main deployment."""
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://example.test")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "fictional-key")
    monkeypatch.setenv("LLM_MODEL", "fixture")
    client.post("/api/login", json={"name": "trainer", "password": "LearnDemo2026!"})
    assert client.post("/api/rehearsal/start", json={"mode": "gateway"}).status_code == 200
    assert client.get("/health").json()["mode"] == "gateway"
    assert client.get("/ready").json()["mode"] == "demo"
    monkeypatch.setattr(db, "DB", db.DB.parent / "missing-main.db")
    assert client.get("/health").json()["mode"] == "gateway"
    assert client.get("/ready").status_code == 503


@pytest.mark.parametrize("sink_error", [OSError, ValueError])
def test_logging_sink_failure_preserves_learning_write_and_response(client, monkeypatch, sink_error):
    """Unavailable/closed stderr cannot turn a persisted learning write into a failure."""
    client.post("/api/login", json={"name": "learner", "password": "LearnDemo2026!"})
    course = next(course for course in client.get("/api/state").json()["courses"] if "readiness" in course["content"])

    class BrokenSink:
        """Simulate a missing pipe or a closed output stream."""

        def write(self, text):
            """Fail without a secondary raw-error fallback."""
            raise sink_error("private-sink-message")

    with monkeypatch.context() as patch:
        patch.setattr("src.utils.logging.sys.stderr", BrokenSink())
        response = client.post("/api/learning/start", json={"course_id": course["id"]})
        assert response.status_code == 200
        session = response.json()
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-ID"])
        saved = client.get(f"/api/learning/{session['id']}")
        assert saved.status_code == 200
        assert saved.json()["id"] == session["id"]
