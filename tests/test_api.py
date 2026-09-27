import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.tools import db_queries as db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "api.db")
    with TestClient(app) as client:
        yield client


def login(client, name="learner"):
    response = client.post(
        "/api/login", json={"name": name, "password": "LearnDemo2026!"}
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]


def test_web_and_auth(client):
    assert client.get("/").status_code == 200
    assert client.get("/chat").headers["content-type"].startswith("text/html")
    assert client.get("/static/app.js").status_code == 200
    assert client.post("/chat", json={"question": "hello"}).status_code == 401
    login(client)
    assert (
        client.post("/api/document", json={"title": "x", "body": "a" * 100}).status_code
        == 403
    )
    assert client.post("/chat", json={"question": "  "}).status_code == 422
    answer = client.post("/chat", json={"question": "missing receipt"})
    assert answer.status_code == 200, answer.text
    assert answer.json()["sources"]
    assert len(client.get("/api/state").json()["chats"]) == 1
    client.post("/api/logout", json={})
    assert client.get("/api/state").status_code == 401


def test_boundary_guards(client):
    assert (
        client.post(
            "/api/login", json={}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.post("/api/login", content="x" * 200001).status_code == 413
    login(client)
    assert client.post("/api/attempt", json={"course_id": 1}).status_code == 400


def test_trainer_to_learner_journey(client):
    login(client, "trainer")
    initial = client.get("/api/state").json()
    course = initial["courses"][0]
    assert client.post("/api/course/create", json={"document_id": 1}).status_code == 200
    draft = client.get("/api/state").json()["courses"][-1]
    assert draft["status"] == "draft"
    assert (
        client.post(
            "/api/course/publish", json={"id": draft["id"], "content": draft["content"]}
        ).status_code
        == 200
    )
    client.post("/api/logout", json={})
    login(client)
    visible = client.get("/api/state").json()["courses"][0]
    assert "answer" not in visible["content"]["assessment_questions"][0]
    pre = client.post(
        "/api/attempt",
        json={"course_id": 1, "phase": "assessment", "answers": [1, 2, 0, 0]},
    )
    assert pre.status_code == 400
    diagnostic = [q["answer"] for q in course["content"]["questions"]]
    result = client.post(
        "/api/attempt",
        json={"course_id": 1, "phase": "diagnostic", "answers": diagnostic},
    )
    assert result.json()["next_action"] == "take_assessment"
    final = [q["answer"] for q in course["content"]["assessment_questions"]]
    result = client.post(
        "/api/attempt", json={"course_id": 1, "phase": "assessment", "answers": final}
    )
    assert result.json()["next_action"] == "completed"
    assert len(client.get("/api/state").json()["attempts"]) == 2


def test_malformed_approval_and_course(client):
    login(client, "trainer")
    assert (
        client.post(
            "/api/document/approve", json={"id": 1, "approved": "false"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/document/approve", json={"id": 999, "approved": True}
        ).status_code
        == 400
    )
    client.post("/api/course/create", json={"document_id": 1})
    draft = client.get("/api/state").json()["courses"][-1]
    draft["content"]["lessons"] = [None]
    assert (
        client.post(
            "/api/course/publish", json={"id": draft["id"], "content": draft["content"]}
        ).status_code
        == 400
    )
