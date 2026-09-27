import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.tools import db_queries as db
from src.workflows.rehearsal import lookup


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "main.db")
    db.init()
    with TestClient(app) as client:
        client.post(
            "/api/login", json={"name": "trainer", "password": "LearnDemo2026!"}
        )
        yield client


def test_rehearsal_isolated_and_return_restores_main_session(workspace):
    client = workspace
    before = client.get("/api/state").json()
    assert client.post("/api/rehearsal/start", json={"mode": "demo"}).status_code == 200
    token = client.cookies.get("rehearsal")
    assert lookup(token)[1] == "demo"
    state = client.get("/api/state").json()
    assert state["rehearsal"] is True
    assert state["user"]["name"] == "learner"
    assert state["learning_sessions"] == []
    course = next(c for c in state["courses"] if "readiness" in c["content"])
    assert "version 2" not in course["title"]
    assert (
        client.post("/api/learning/start", json={"course_id": course["id"]}).status_code
        == 200
    )
    with TestClient(app) as other:
        other.post("/api/login", json={"name": "trainer", "password": "LearnDemo2026!"})
        assert (
            other.get("/api/state").json()["learning_sessions"]
            == before["learning_sessions"]
        )
        assert other.get("/api/state").json()["rehearsal"] is False
    assert client.post("/api/rehearsal/exit", json={}).status_code == 200
    restored = client.get("/api/state").json()
    assert restored["user"]["name"] == "trainer"
    assert restored["learning_sessions"] == before["learning_sessions"]
    assert restored["courses"] == before["courses"]
    assert lookup(token)[0].is_file()  # No deletion on exit.


def test_requires_trainer_and_rejects_invalid_context(workspace):
    client = workspace
    client.post("/api/login", json={"name": "learner", "password": "LearnDemo2026!"})
    assert client.post("/api/rehearsal/start", json={"mode": "demo"}).status_code == 403
    with pytest.raises(ValueError):
        lookup("../main")
    client.cookies.set("rehearsal", "0" * 32)
    assert client.get("/api/state").status_code == 400
    context = client.get("/api/rehearsal/context").json()
    assert context["rehearsal"] is True
    assert "Unavailable" in context["mode"]
    assert client.post("/api/rehearsal/exit", json={}).status_code == 200


def test_each_rehearsal_is_new_and_mode_is_request_local(workspace, monkeypatch):
    client = workspace
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://example.test")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "fixture")
    monkeypatch.setenv("LLM_MODEL", "fixture")
    assert (
        client.post("/api/rehearsal/start", json={"mode": "gateway"}).status_code == 200
    )
    first = client.cookies.get("rehearsal")
    assert client.get("/health").json()["mode"] == "gateway"
    with TestClient(app) as other:
        assert other.get("/health").json()["mode"] == "demo"
    client.post("/api/login", json={"name": "trainer", "password": "LearnDemo2026!"})
    assert client.post("/api/rehearsal/start", json={"mode": "demo"}).status_code == 200
    assert client.cookies.get("rehearsal") != first
    assert client.get("/health").json()["mode"] == "demo"
    assert lookup(first)[0].is_file()
    client.post("/api/rehearsal/exit", json={})
    assert client.get("/api/state").json()["user"]["name"] == "trainer"
