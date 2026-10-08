"""Offline rehearsal with known fixture answers; not participant evidence.

Run from the workspace parent. Retains a fresh rehearsal DB for inspection.
Requires the development test dependencies for the existing fixture helpers.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

os.environ["AGENT_MODE"] = "demo"
sys.path.insert(0, str(Path(__file__).resolve().parent))
workspace = Path.cwd() / ("pilot-rehearsal-" + uuid4().hex)
workspace.mkdir()
os.environ["TRAINING_DB"] = str(workspace / "rehearsal.db")

from src.agents.learning_coach import advance
from src.core.config import Settings
from src.tools import db_queries as db
from src.workflows import change_impact as changes
from src.workflows import readiness as r
from tests.test_readiness import answer_for


def finish(user, session, course):
    """Complete the fixture journey using known answers within a bounded loop."""
    for _ in range(30):
        if session["state"] == "ready":
            return session
        issued = advance(user, session["id"], Settings(mode="demo"))["session"]
        activity = issued["activity"]
        session = r.submit(user, session["id"], activity["id"],
                           answer_for(course, activity))["session"]
    raise AssertionError("Journey exceeded the rehearsal activity limit")


def main():
    """Verify the fictional update journey and write a non-participant report."""
    db.init()
    learner = db.user(db.login("learner", "LearnDemo2026!"))
    trainer = db.user(db.login("trainer", "LearnDemo2026!"))
    with db.connect() as connection:
        course = dict(connection.execute(
            "SELECT * FROM courses WHERE title LIKE 'Expense procedure readiness%'"
        ).fetchone())
    course["content"] = json.loads(course["content"])
    session = r.start(learner, course["id"])
    while session["state"] == "diagnosing":
        issued = advance(learner, session["id"], Settings(mode="demo"))["session"]
        activity = issued["activity"]
        answer = answer_for(course, activity)
        if activity["objective_id"] == "receipt_evidence":
            answer = (answer + 1) % len(activity["options"])
        session = r.submit(learner, session["id"], activity["id"], answer)["session"]
    assert session["state"] != "ready"
    assert any(a["objective_id"] == "receipt_evidence" and a["kind"] == "lesson"
               for a in session["eligible_actions"])
    original = finish(learner, session, course)
    assert original["score"] == 100
    resumed = r.get(learner, original["id"])
    assert resumed["decisions"] == original["decisions"]
    assert all(d["mode"] == "demo" for d in resumed["decisions"])
    draft = changes.fictional_update(trainer, course["id"])
    mapping = draft["comparison"]["objectives"]
    refresh = [o["id"] for o in mapping if o["required_refresh"]]
    carry = [o["id"] for o in mapping if not o["required_refresh"]]
    assert refresh == ["receipt_evidence"] and len(carry) == 3
    # Exact fixture mapping; does not represent human content approval.
    assert changes.activate(trainer, draft["id"], refresh, carry)["assigned"] == 1
    successor = r.start(learner, draft["new_course_id"])
    assert successor["state"] != "ready" and successor["score"] == 75
    assert sum(bool(o["carried_from_session"]) for o in successor["objectives"]) == 3
    assert all(a["objective_id"] == "receipt_evidence"
               for a in successor["eligible_actions"])
    target = dict(course, id=draft["new_course_id"], content=draft["new_content"])
    updated = finish(learner, successor, target)
    prior = r.get(learner, original["id"])
    assert prior["state"] == "superseded"
    assert prior["decisions"] == original["decisions"]
    assert updated["state"] == "ready" and updated["score"] == 100
    report = {
        "timestamp_singapore": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "type": "automated offline rehearsal with known fixture answers",
        "mode": "demo", "participant_count": 0, "database": str(db.DB),
        "checks": {name: "pass" for name in [
            "missed_receipt_diagnostic_blocks_readiness",
            "receipt_coaching_available", "fresh_cases_reach_original_readiness",
            "decision_records_persist_in_demo_mode",
            "revision_requires_one_objective_refresh",
            "three_objectives_carry_prior_evidence", "successor_pending_at_75_percent",
            "updated_fresh_case_restores_readiness", "prior_history_preserved",
        ]},
        "limitations": [
            "No browser interaction or human usability observation",
            "No live gateway requests or model quality assessment",
            "No held-out participant answers or learning-effectiveness measurement",
            "Automatic fixture mapping does not replace trainer content review",
        ],
    }
    (workspace / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
