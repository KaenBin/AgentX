import copy
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.tools import db_queries as db
from src.core.state import snapshot
from src.workflows import readiness as r, change_impact as changes
from src.workflows.router import act
from tests.test_readiness import setup, answer_for, finish_diagnostic


def test_equivalent_evidence_survives_a_second_approved_revision(setup):
    users, course = setup
    complete(users["learner"], course)
    second = changes.fictional_update(users["trainer"], course["id"])
    changes.activate(users["trainer"], second["id"], *mapping(second))
    target = dict(course, id=second["new_course_id"], content=second["new_content"])
    complete(users["learner"], target)
    third = changes.create(
        users["trainer"],
        target["id"],
        "Version 3 equivalent policy",
        second["new_source"],
        second["new_content"],
    )
    assert third["version"] == 3 and third["root_course_id"] == course["id"]
    assert mapping(third)[0] == []
    changes.activate(users["trainer"], third["id"], *mapping(third))
    state = r.start(users["learner"], third["new_course_id"])
    assert state["state"] == "ready"
    assert all(o["carried_from_session"] for o in state["objectives"])


def mapping(draft):
    objs = draft["comparison"]["objectives"]
    return (
        [o["id"] for o in objs if o["required_refresh"]],
        [o["id"] for o in objs if not o["required_refresh"]],
    )


def complete(user, course, session=None):
    session = session or r.start(user, course["id"])
    for _ in range(30):
        if session["state"] == "ready":
            return session
        session = r.issue(user, session["id"])
        activity = session["activity"]
        session = r.submit(
            user, session["id"], activity["id"], answer_for(course, activity)
        )["session"]
    raise AssertionError("Journey did not complete")


def test_draft_is_private_and_comparison_identifies_one_objective(setup):
    users, course = setup
    draft = changes.fictional_update(users["trainer"], course["id"])
    assert mapping(draft)[0] == ["receipt_evidence"]
    assert len(mapping(draft)[1]) == 3
    assert "written Finance exception" in draft["comparison"]["diff"]
    assert snapshot(users["learner"])["procedure_revisions"] == []
    assert draft["new_course_id"] not in {
        c["id"] for c in snapshot(users["learner"])["courses"]
    }
    with pytest.raises(ValueError):
        r.start(users["learner"], draft["new_course_id"])


def test_activation_refreshes_one_step_preserves_history_and_equivalent_evidence(setup):
    users, course = setup
    old = complete(users["learner"], course)
    with db.connect() as c:
        records = [
            tuple(x) for x in c.execute("SELECT * FROM learning_activities ORDER BY id")
        ]
    draft = changes.fictional_update(users["trainer"], course["id"])
    result = changes.activate(users["trainer"], draft["id"], *mapping(draft))
    assert result["assigned"] == 1
    sessions = r.list_sessions(users["learner"])
    prior = next(s for s in sessions if s["id"] == old["id"])
    new = next(s for s in sessions if s["course_id"] == draft["new_course_id"])
    assert prior["state"] == "superseded"
    assert all(o["demonstrated"] for o in prior["objectives"])
    assert new["score"] == 75 and new["state"] != "ready"
    assert sum(bool(o["carried_from_session"]) for o in new["objectives"]) == 3
    assert [a["objective_id"] for a in new["eligible_actions"]] == ["receipt_evidence"]
    assert new["eligible_actions"][0]["kind"] == "lesson"
    target = dict(course, id=draft["new_course_id"], content=draft["new_content"])
    assert complete(users["learner"], target, new)["state"] == "ready"
    with db.connect() as c:
        assert [
            tuple(x)
            for x in c.execute(
                "SELECT * FROM learning_activities WHERE session_id=? ORDER BY id",
                (old["id"],),
            )
        ] == records
    assert course["id"] not in {c["id"] for c in snapshot(users["learner"])["courses"]}


def test_old_pending_activity_cannot_be_submitted_after_activation(setup):
    users, course = setup
    old = r.issue(users["learner"], r.start(users["learner"], course["id"])["id"])
    draft = changes.fictional_update(users["trainer"], course["id"])
    changes.activate(users["trainer"], draft["id"], *mapping(draft))
    with pytest.raises(ValueError, match="superseded"):
        r.submit(users["learner"], old["id"], old["activity"]["id"], 0)
    with pytest.raises(ValueError):
        r.start(users["learner"], course["id"])
    with pytest.raises(ValueError):
        r.issue(users["learner"], old["id"])
    with pytest.raises(ValueError):
        act(
            users["trainer"],
            "/api/document/approve",
            {"id": course["document_id"], "approved": True},
        )


def test_approval_cannot_skip_changed_objective_and_has_no_partial_writes(setup):
    users, course = setup
    draft = changes.fictional_update(users["trainer"], course["id"])
    all_ids = [o["id"] for o in draft["comparison"]["objectives"]]
    with pytest.raises(ValueError, match="changed objectives"):
        changes.activate(users["trainer"], draft["id"], [], all_ids)
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM procedure_successors").fetchone()[0] == 0
        assert (
            c.execute(
                "SELECT approved FROM documents WHERE id=?", (course["document_id"],)
            ).fetchone()[0]
            == 1
        )


def test_only_trainers_can_draft_or_activate(setup):
    users, course = setup
    with pytest.raises(PermissionError):
        changes.fictional_update(users["learner"], course["id"])
    draft = changes.fictional_update(users["trainer"], course["id"])
    with pytest.raises(PermissionError):
        changes.activate(users["learner"], draft["id"], *mapping(draft))


def test_repeated_and_concurrent_activation_is_idempotent(setup):
    users, course = setup
    r.start(users["learner"], course["id"])
    draft = changes.fictional_update(users["trainer"], course["id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: changes.activate(
                    users["trainer"], draft["id"], *mapping(draft)
                ),
                range(2),
            )
        )
    assert all(x["ok"] for x in results)
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM procedure_successors").fetchone()[0] == 1
        assert (
            c.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE course_id=?",
                (draft["new_course_id"],),
            ).fetchone()[0]
            == 1
        )


def test_stale_content_and_conflicting_drafts_are_rejected(setup):
    users, course = setup
    first = changes.fictional_update(users["trainer"], course["id"])
    second = changes.fictional_update(users["trainer"], course["id"])
    with db.connect() as c:
        c.execute(
            "UPDATE courses SET title='changed after review' WHERE id=?",
            (second["new_course_id"],),
        )
    with pytest.raises(ValueError, match="changed after comparison"):
        changes.activate(users["trainer"], second["id"], *mapping(second))
    changes.activate(users["trainer"], first["id"], *mapping(first))
    with pytest.raises(ValueError, match="no longer current"):
        changes.activate(users["trainer"], second["id"], *mapping(second))


def test_reused_refresh_questions_are_rejected(setup):
    users, course = setup
    draft = changes.fictional_update(users["trainer"], course["id"])
    content = copy.deepcopy(draft["new_content"])
    content["readiness"]["objectives"][0]["reassessments"] = copy.deepcopy(
        course["content"]["readiness"]["objectives"][0]["reassessments"]
    )
    reused = changes.create(
        users["trainer"], course["id"], "Reused fixture", draft["new_source"], content
    )
    with pytest.raises(ValueError, match="new reassessment prompts"):
        changes.activate(users["trainer"], reused["id"], *mapping(reused))


def test_unpassed_equivalent_objective_avoids_previously_issued_case(setup):
    users, course = setup
    user = users["learner"]
    session = finish_diagnostic(user, course, r.start(user, course["id"]))
    choice = next(
        a
        for a in session["eligible_actions"]
        if a["objective_id"] == "submission_timing"
    )
    session = r.issue(user, session["id"], choice["activity_id"])
    exposed = session["activity"]["prompt"]
    draft = changes.fictional_update(users["trainer"], course["id"])
    changes.activate(users["trainer"], draft["id"], *mapping(draft))
    new = r.start(user, draft["new_course_id"])
    target = dict(course, id=draft["new_course_id"], content=draft["new_content"])
    new = finish_diagnostic(user, target, new)
    choice = next(
        a for a in new["eligible_actions"] if a["objective_id"] == "submission_timing"
    )
    new = r.issue(user, new["id"], choice["activity_id"])
    assert new["activity"]["prompt"] != exposed
    assert new["activity"]["activity_id"].endswith("case_2")


def test_revision_api_and_generic_approval_bypass(setup):
    users, course = setup
    with TestClient(app) as client:
        client.post(
            "/api/login", json={"name": "trainer", "password": "LearnDemo2026!"}
        )
        response = client.post("/api/revisions/demo", json={"course_id": course["id"]})
        assert response.status_code == 200
        draft = response.json()
        with db.connect() as c:
            did = c.execute(
                "SELECT document_id FROM courses WHERE id=?", (draft["new_course_id"],)
            ).fetchone()[0]
        assert (
            client.post(
                "/api/document/approve", json={"id": did, "approved": True}
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/course/publish",
                json={"id": draft["new_course_id"], "content": draft["new_content"]},
            ).status_code
            == 400
        )
        affected, equivalent = mapping(draft)
        response = client.post(
            f"/api/revisions/{draft['id']}/activate",
            json={"affected_ids": affected, "equivalent_ids": equivalent},
        )
        assert response.status_code == 200, response.text
        client.post("/api/logout", json={})
        client.post("/api/login", json={"name": "alex", "password": "LearnDemo2026!"})
        assert client.get("/api/state").json()["procedure_revisions"] == []
        assert (
            client.post(
                "/api/revisions/demo", json={"course_id": draft["new_course_id"]}
            ).status_code
            == 403
        )
