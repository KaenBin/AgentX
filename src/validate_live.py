"""Opt-in gateway smoke check using only a disposable fictional database.

Run with python -m src.validate_live. No credentials or raw model output are logged.
"""

import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from src.agents.learning_coach import advance
from src.agents.orchestrator import TrainingOrchestrator
from src.agents.worker import GatewayError, GatewayWorker
from src.core.config import Settings
from src.tools import db_queries as db
from src.workflows import readiness


def check(settings, worker=None):
    """Run in a standalone process; temporarily redirect the process-local DB."""
    settings = replace(settings, mode="gateway")
    settings.validate()
    worker = worker or GatewayWorker(settings)
    previous_db = db.DB
    results = []
    with TemporaryDirectory(prefix="agentx-live-check-") as directory:
        try:
            db.DB = Path(directory) / "fictional.db"
            db.init()
            user = db.user(db.login("learner", "LearnDemo2026!"))
            with db.connect() as connection:
                course = connection.execute(
                    "SELECT * FROM courses WHERE title=?",
                    ("Expense procedure readiness — fictional pilot",),
                ).fetchone()
            objectives = json.loads(course["content"])["readiness"]["objectives"]
            session = readiness.start(user, course["id"])
            # Establish a known missed step without asking the model to grade it.
            while session["state"] == "diagnosing":
                session = readiness.issue(user, session["id"])
                activity = session["activity"]
                objective = next(
                    o for o in objectives if o["id"] == activity["objective_id"]
                )
                answer = objective["diagnostic"]["answer"]
                if objective["id"] == "receipt_evidence":
                    answer = (answer + 1) % len(activity["options"])
                session = readiness.submit(user, session["id"], activity["id"], answer)[
                    "session"
                ]
            eligible = {a["activity_id"] for a in session["eligible_actions"]}
            selected = advance(user, session["id"], settings, worker)
            after = selected["session"]
            if (
                after["activity"]["activity_id"] not in eligible
                or after["score"] != session["score"]
                or after["state"] == "ready"
            ):
                raise GatewayError("Live selection violated readiness invariants")
            results.append(
                {
                    "check": "eligible_activity_without_score_change",
                    "passed": True,
                    "activity_kind": after["activity"]["kind"],
                    "objective": after["activity"]["objective_id"],
                    "reason": selected["reason"],
                }
            )
            coach = TrainingOrchestrator(settings, worker)
            supported = coach.run(user, "What should I do if my receipt is missing?")
            if not supported["sources"] or supported["out_of_scope"]:
                raise GatewayError(
                    "Live policy answer did not retrieve approved evidence"
                )
            results.append(
                {
                    "check": "approved_policy_citations",
                    "passed": True,
                    "tools": supported["trace"],
                }
            )
            unsupported = coach.run(user, "What is the capital of France?")
            if not unsupported["out_of_scope"]:
                raise GatewayError("Unsupported question was not referred to a trainer")
            results.append(
                {
                    "check": "unsupported_question_referral",
                    "passed": True,
                    "tools": unsupported["trace"],
                }
            )
        finally:
            db.DB = previous_db
    return results


def main():
    settings = Settings()
    missing = [
        name
        for name, value in [
            ("LLM_GATEWAY_URL", settings.gateway_url),
            ("LLM_GATEWAY_API_KEY", settings.gateway_api_key),
            ("LLM_MODEL", settings.model),
        ]
        if not value
    ]
    if missing:
        print(json.dumps({"status": "blocked", "missing_settings": missing}))
        return 2
    try:
        results = check(settings)
    except Exception:
        # Never print upstream exception bodies, URLs, prompts or credentials.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "message": "Gateway validation failed. Check connectivity, configuration and structured-output support; then retry.",
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": results,
                "limits": "Smoke checks only; citation presence does not establish factual correctness or learning effectiveness.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
