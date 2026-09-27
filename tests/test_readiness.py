import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.core.state import snapshot
from src.core.config import Settings
from src.tools import db_queries as db
from src.tools.training_tools import execute
from src.workflows import readiness as r
from src.workflows.readiness_content import validate_readiness
from src.agents.learning_coach import advance
from src.agents.worker import GatewayError


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "readiness.db")
    db.init()
    users = {
        name: db.user(db.login(name, "LearnDemo2026!"))
        for name in ["learner", "alex", "trainer"]
    }
    with db.connect() as c:
        course = dict(
            c.execute(
                "SELECT * FROM courses WHERE title LIKE 'Expense procedure readiness%' "
            ).fetchone()
        )
    course["content"] = json.loads(course["content"])
    return users, course


def answer_for(course, activity):
    if activity["kind"] == "lesson":
        return None
    obj = next(
        o
        for o in course["content"]["readiness"]["objectives"]
        if o["id"] == activity["objective_id"]
    )
    return next(
        q["answer"]
        for q in [obj["diagnostic"], *obj["reassessments"]]
        if q["id"] == activity["activity_id"]
    )


def finish_diagnostic(user, course, session, miss=None):
    while session["state"] == "diagnosing":
        session = r.issue(user, session["id"])
        activity = session["activity"]
        answer = answer_for(course, activity)
        if activity["objective_id"] == miss:
            answer = (answer + 1) % len(activity["options"])
        session = r.submit(user, session["id"], activity["id"], answer)["session"]
    return session


def test_additive_seed_and_migration_are_repeatable(setup):
    users, course = setup
    with db.connect() as c:
        before = [tuple(x) for x in c.execute("SELECT * FROM courses")]
    db.init()
    db.init()
    with db.connect() as c:
        assert [tuple(x) for x in c.execute("SELECT * FROM courses")] == before
        assert {
            x[0] for x in c.execute("SELECT version FROM readiness_migrations")
        } == {1, 2}
    assert "readiness" in course["content"]


def test_start_resume_and_no_future_case_or_answer_leak(setup):
    users, course = setup
    session = r.start(users["learner"], course["id"])
    assert r.start(users["learner"], course["id"])["id"] == session["id"]
    view = snapshot(users["learner"])
    visible = next(c for c in view["courses"] if c["id"] == course["id"])
    assert "reassessments" not in json.dumps(visible)
    assert course["content"]["readiness"]["objectives"][0]["reassessments"][0][
        "prompt"
    ] not in json.dumps(view)
    issued = r.issue(users["learner"], session["id"])
    assert "answer" not in issued["activity"]
    assert (
        r.issue(users["learner"], session["id"])["activity"]["id"]
        == issued["activity"]["id"]
    )


def test_wrong_diagnostic_coaching_fresh_reassessment_then_ready(setup):
    users, course = setup
    user = users["learner"]
    session = finish_diagnostic(
        user, course, r.start(user, course["id"]), "receipt_evidence"
    )
    assert session["state"] != "ready"
    receipt = next(
        a
        for a in session["eligible_actions"]
        if a["objective_id"] == "receipt_evidence"
    )
    assert receipt["kind"] == "lesson"
    session = r.issue(user, session["id"], receipt["activity_id"])
    assert "duplicate" in session["activity"]["text"]
    while session["state"] != "ready":
        if not session["activity"]:
            session = r.issue(user, session["id"])
        activity = session["activity"]
        session = r.submit(
            user, session["id"], activity["id"], answer_for(course, activity)
        )["session"]
    assert session["score"] == 100
    assert all(o["demonstrated"] for o in session["objectives"])


def test_decision_record_persists_mode_evidence_and_outcome(setup):
    users, course = setup
    user = users["learner"]
    session = r.start(user, course["id"])
    response = advance(user, session["id"], Settings(mode="demo"))
    issued = response["session"]
    decision = issued["decisions"][0]
    assert decision["mode"] == "demo"
    assert decision["diagnostic_correct"] is None
    assert decision["source_section"] == issued["activity"]["source_section"]
    assert decision["submitted"] is None
    assert "answer" not in decision
    assert "prompt" not in decision
    assert advance(user, session["id"], Settings(mode="demo"))["session"][
        "decisions"
    ] == [decision]
    r.submit(
        user,
        session["id"],
        issued["activity"]["id"],
        answer_for(course, issued["activity"]),
    )
    saved = r.get(user, session["id"])["decisions"][0]
    assert saved["correct"] is True
    assert saved["submitted"] is not None
    assert (
        saved["diagnostic_correct"] is None
    )  # Snapshot remains the evidence at selection.
    assert r.list_sessions(users["alex"]) == []
    assert r.get(users["trainer"], session["id"])["decisions"] == [saved]


def test_decision_record_is_not_relabelled_by_duplicate_issue(setup):
    users, course = setup
    user = users["learner"]
    sid = r.start(user, course["id"])["id"]
    original = r.issue(user, sid, selection_mode="gateway")
    resumed = r.issue(user, sid, selection_mode="demo")
    assert resumed["decisions"] == original["decisions"]
    assert resumed["decisions"][0]["mode"] == "gateway"


def test_duplicate_answer_is_idempotent_and_cannot_be_changed(setup):
    users, course = setup
    user = users["learner"]
    session = r.issue(user, r.start(user, course["id"])["id"])
    a = session["activity"]
    first = r.submit(user, session["id"], a["id"], 0)
    assert r.submit(user, session["id"], a["id"], 0) == first
    with pytest.raises(ValueError, match="cannot be changed"):
        r.submit(user, session["id"], a["id"], 1)
    with db.connect() as c:
        assert (
            c.execute(
                "SELECT COUNT(*) FROM learning_activities WHERE submitted IS NOT NULL"
            ).fetchone()[0]
            == 1
        )


def test_no_reuse_and_exhaustion_creates_one_review(setup):
    users, course = setup
    user = users["learner"]
    session = finish_diagnostic(user, course, r.start(user, course["id"]))
    case_ids = []
    for _ in range(12):
        choice = next(
            (
                a
                for a in session["eligible_actions"]
                if a["objective_id"] == "receipt_evidence"
            ),
            None,
        )
        if not choice:
            break
        session = r.issue(user, session["id"], choice["activity_id"])
        a = session["activity"]
        answer = None
        if a["kind"] != "lesson":
            case_ids.append(a["activity_id"])
            answer = (answer_for(course, a) + 1) % len(a["options"])
        session = r.submit(user, session["id"], a["id"], answer)["session"]
    assert len(case_ids) == len(set(case_ids)) == 2
    assert len(session["reviews"]) == 1
    assert session["objectives"][0]["needs_trainer"]
    with pytest.raises(ValueError):
        r.issue(user, session["id"], case_ids[0])
    r.resolve_review(
        users["trainer"],
        session["reviews"][0]["id"],
        "Review the evidence rule with me.",
    )
    assert r.get(user, session["id"])["state"] != "ready"


def test_critical_failure_blocks_eighty_percent(setup):
    users, course = setup
    content = copy.deepcopy(course["content"])
    fifth = copy.deepcopy(content["readiness"]["objectives"][-1])
    fifth["id"] = "supporting_extra"
    for q in [fifth["diagnostic"], *fifth["reassessments"]]:
        q["id"] += "_extra"
        q["prompt"] += " Extra fixture."
    content["readiness"]["objectives"].append(fifth)
    with db.connect() as c:
        cid = c.execute(
            "INSERT INTO courses(title,document_id,content,status) VALUES('five objective fixture',?,?, 'published')",
            (course["document_id"], json.dumps(content)),
        ).lastrowid
    fixture = dict(course, id=cid, content=content)
    user = users["learner"]
    session = finish_diagnostic(user, fixture, r.start(user, cid))
    while session["eligible_actions"]:
        session = r.issue(user, session["id"])
        a = session["activity"]
        answer = answer_for(fixture, a)
        if a["kind"] != "lesson" and a["objective_id"] == "receipt_evidence":
            answer = (answer + 1) % len(a["options"])
        session = r.submit(user, session["id"], a["id"], answer)["session"]
    assert session["score"] == 80
    assert session["state"] == "needs_trainer"


def test_authorization_withdrawal_and_unissued_answers(setup):
    users, course = setup
    user = users["learner"]
    session = r.issue(user, r.start(user, course["id"])["id"])
    with pytest.raises(PermissionError):
        r.get(users["alex"], session["id"])
    with pytest.raises(PermissionError):
        r.submit(users["trainer"], session["id"], session["activity"]["id"], 0)
    with pytest.raises(ValueError):
        r.submit(user, session["id"], 999, 0)
    with db.connect() as c:
        c.execute(
            "UPDATE documents SET approved=0 WHERE id=?", (course["document_id"],)
        )
    assert r.get(user, session["id"])["state"] == "blocked"
    with pytest.raises(ValueError):
        r.submit(user, session["id"], session["activity"]["id"], 0)
    with pytest.raises(ValueError):
        r.issue(user, session["id"])


def test_concurrent_start_and_issue_do_not_duplicate(setup):
    users, course = setup
    user = users["learner"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        sessions = list(pool.map(lambda _: r.start(user, course["id"]), range(2)))
        activities = list(
            pool.map(lambda _: r.issue(user, sessions[0]["id"]), range(2))
        )
    assert sessions[0]["id"] == sessions[1]["id"]
    assert activities[0]["activity"]["id"] == activities[1]["activity"]["id"]


def test_live_agent_selects_eligible_action_and_cannot_invent_one(setup):
    users, course = setup
    user = users["learner"]
    session = r.start(user, course["id"])
    choice = session["eligible_actions"][-1]
    settings = Settings(
        mode="gateway",
        gateway_url="https://example.test",
        gateway_api_key="test",
        model="test",
    )

    class Worker:
        def chat(self, messages):
            return json.dumps(
                {
                    "tool": "select_approved_activity",
                    "args": {
                        "session_id": session["id"],
                        "activity_id": choice["activity_id"],
                    },
                }
            )

    response = advance(user, session["id"], settings, Worker())
    assert response["session"]["activity"]["activity_id"] == choice["activity_id"]
    assert response["selection_mode"] == "gateway"
    other = r.start(users["alex"], course["id"])
    with pytest.raises(GatewayError):
        advance(users["alex"], other["id"], settings, Worker())
    assert r.get(users["alex"], other["id"])["activity"] is None


def test_live_selection_repairs_format_without_executing_invalid_output(setup):
    users, course = setup
    user = users["learner"]
    session = r.start(user, course["id"])
    choice = session["eligible_actions"][0]
    settings = Settings(
        mode="gateway",
        gateway_url="https://example.test",
        gateway_api_key="test",
        model="test",
    )

    class Worker:
        calls = 0

        def chat(self, messages):
            self.calls += 1
            assert r.get(user, session["id"])["activity"] is None
            if self.calls == 1:
                return "Here is my choice: {}"
            return json.dumps(
                {
                    "tool": "select_approved_activity",
                    "args": {
                        "session_id": session["id"],
                        "activity_id": choice["activity_id"],
                    },
                }
            )

    worker = Worker()
    result = advance(user, session["id"], settings, worker)
    assert worker.calls == 2
    assert result["session"]["activity"]["activity_id"] == choice["activity_id"]
    assert result["session"]["score"] == session["score"]


def test_live_selection_repair_cannot_issue_invented_activity(setup):
    users, course = setup
    user = users["learner"]
    session = r.start(user, course["id"])
    settings = Settings(
        mode="gateway",
        gateway_url="https://example.test",
        gateway_api_key="test",
        model="test",
    )

    class Worker:
        calls = 0

        def chat(self, messages):
            self.calls += 1
            if self.calls == 1:
                return "not json"
            return json.dumps(
                {
                    "tool": "select_approved_activity",
                    "args": {"session_id": session["id"], "activity_id": "invented"},
                }
            )

    worker = Worker()
    with pytest.raises(GatewayError):
        advance(user, session["id"], settings, worker)
    assert worker.calls == 2
    assert r.get(user, session["id"])["activity"] is None


def test_withdrawal_while_model_selects_rechecked(setup):
    users, course = setup
    user = users["learner"]
    session = r.start(user, course["id"])

    class Worker:
        def chat(self, messages):
            with db.connect() as c:
                c.execute(
                    "UPDATE documents SET approved=0 WHERE id=?",
                    (course["document_id"],),
                )
            return json.dumps(
                {
                    "tool": "select_approved_activity",
                    "args": {
                        "session_id": session["id"],
                        "activity_id": session["eligible_actions"][0]["activity_id"],
                    },
                }
            )

    settings = Settings(
        mode="gateway",
        gateway_url="https://example.test",
        gateway_api_key="test",
        model="test",
    )
    with pytest.raises(ValueError, match="withdrawn"):
        advance(user, session["id"], settings, Worker())


def test_review_request_deduplication_and_trainer_resolution(setup):
    users, course = setup
    session = r.start(users["learner"], course["id"])
    for _ in range(2):
        session = r.request_review(
            users["learner"], session["id"], "What if the supplier closed?"
        )
    assert len(session["reviews"]) == 1
    review_id = session["reviews"][0]["id"]
    with pytest.raises(PermissionError):
        r.resolve_review(users["learner"], review_id, "Pass me")
    r.resolve_review(
        users["trainer"], review_id, "Ask Finance to review this exception."
    )
    assert r.get(users["learner"], session["id"])["reviews"][0]["status"] == "resolved"
    assert r.get(users["learner"], session["id"])["state"] == "diagnosing"


def test_api_and_agent_readiness_tools(setup):
    users, course = setup
    with TestClient(app) as client:
        client.post(
            "/api/login", json={"name": "learner", "password": "LearnDemo2026!"}
        )
        session = client.post(
            "/api/learning/start", json={"course_id": course["id"]}
        ).json()
        response = client.post(f"/api/learning/{session['id']}/next", json={})
        assert response.status_code == 200
        activity = response.json()["session"]["activity"]
        invalid = client.post(
            f"/api/learning/{session['id']}/answer",
            json={"issued_id": activity["id"], "answer": True},
        )
        assert invalid.status_code == 422
        result = client.post(
            f"/api/learning/{session['id']}/answer",
            json={"issued_id": activity["id"], "answer": 0},
        )
        assert result.status_code == 200
        assert client.get(f"/api/learning/{session['id']}").status_code == 200
        assert (
            client.post(
                "/api/attempt",
                json={"course_id": course["id"], "phase": "diagnostic", "answers": []},
            ).status_code
            == 400
        )
    state = execute(users["learner"], "get_learning_state", {})
    assert state["sessions"][0]["id"] == session["id"]
    assert execute(users["alex"], "get_learning_state", {}) == {"sessions": []}


def test_readiness_validation_rejects_duplicate_case_and_bad_source(setup):
    _, course = setup
    content = copy.deepcopy(course["content"])
    content["readiness"]["objectives"][0]["reassessments"][1] = copy.deepcopy(
        content["readiness"]["objectives"][0]["reassessments"][0]
    )
    with pytest.raises(ValueError):
        validate_readiness(content)
    with pytest.raises(ValueError):
        validate_readiness(course["content"], 1)


def test_legacy_course_upgrade_preserves_original_content(setup):
    _, course = setup
    with db.connect() as c:
        c.execute("DELETE FROM courses WHERE id=?", (course["id"],))
        legacy = json.loads(
            c.execute("SELECT content FROM courses WHERE id=1").fetchone()[0]
        )
        legacy.pop("assessment_questions")
        original = json.dumps(legacy)
        c.execute("UPDATE courses SET content=? WHERE id=1", (original,))
    db.init()
    with db.connect() as c:
        assert (
            c.execute("SELECT content FROM courses WHERE id=1").fetchone()[0]
            == original
        )
        assert (
            c.execute(
                "SELECT COUNT(*) FROM courses WHERE title LIKE 'Expense procedure readiness%'"
            ).fetchone()[0]
            == 1
        )


def test_demo_chat_uses_readiness_instead_of_legacy_scores(setup):
    from src.agents.orchestrator import TrainingOrchestrator

    users, course = setup
    session = r.start(users["learner"], course["id"])
    result = TrainingOrchestrator().run(users["learner"], "What should I study next?")
    assert "select_approved_activity" in result["trace"]
    assert "Receipt evidence" in result["answer"]
    assert r.get(users["learner"], session["id"])["activity"] is None
