"""Persistent, server-authoritative learning evidence. Models cannot score it."""

import json
import time
from src.tools import db_queries as db


def migrate(c):
    # Additive tables; existing course content and attempts are left intact.
    statements = [
        "CREATE TABLE IF NOT EXISTS readiness_migrations(version INTEGER PRIMARY KEY)",
        """CREATE TABLE IF NOT EXISTS learning_sessions(
            id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),document_id INTEGER NOT NULL REFERENCES documents(id),
            rule_version INTEGER NOT NULL,created REAL NOT NULL,UNIQUE(user_id,course_id))""",
        """CREATE TABLE IF NOT EXISTS learning_activities(
            id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES learning_sessions(id),
            objective_id TEXT NOT NULL,activity_id TEXT NOT NULL,kind TEXT NOT NULL,
            answer INTEGER,correct INTEGER,created REAL NOT NULL,submitted REAL,
            UNIQUE(session_id,activity_id))""",
        """CREATE UNIQUE INDEX IF NOT EXISTS one_pending_learning_activity
            ON learning_activities(session_id) WHERE submitted IS NULL""",
        """CREATE TABLE IF NOT EXISTS learning_reviews(
            id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES learning_sessions(id),
            reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',resolution TEXT,
            created REAL NOT NULL,resolved REAL,UNIQUE(session_id,reason))""",
    ]
    statements.append(
        """CREATE TABLE IF NOT EXISTS learning_decisions(
        activity_id INTEGER PRIMARY KEY REFERENCES learning_activities(id), detail TEXT NOT NULL)"""
    )
    for sql in statements:
        c.execute(sql)
    c.execute("INSERT OR IGNORE INTO readiness_migrations VALUES(1)")
    from src.workflows.change_impact import migrate as migrate_revisions

    migrate_revisions(c)


def _load(c, user, sid, trainer_read=False):
    row = c.execute(
        "SELECT s.*,c.content,c.title,d.title source_title,d.approved,c.status course_status "
        "FROM learning_sessions s JOIN courses c ON c.id=s.course_id "
        "JOIN documents d ON d.id=s.document_id WHERE s.id=?",
        (sid,),
    ).fetchone()
    if not row or (
        row["user_id"] != user["id"]
        and not (trainer_read and user["role"] == "trainer")
    ):
        raise PermissionError("Learning session is unavailable")
    return row, json.loads(row["content"])["readiness"]


def _question(obj, activity_id):
    return next(
        (
            q
            for q in [obj["diagnostic"], *obj["reassessments"]]
            if q["id"] == activity_id
        ),
        None,
    )


def _view(c, row, spec):
    from src.workflows.change_impact import superseded

    successor = superseded(c, row["course_id"])
    inherited = {
        x["objective_id"]: dict(x)
        for x in c.execute(
            "SELECT * FROM learning_carryovers WHERE session_id=?", (row["id"],)
        )
    }
    refreshes = {
        x[0]
        for x in c.execute(
            "SELECT objective_id FROM learning_refreshes WHERE session_id=?",
            (row["id"],),
        )
    }
    # A case already issued in another course is not fresh evidence for this learner.
    exposed = set()
    for previous in c.execute(
        "SELECT a.activity_id,a.objective_id,c.content FROM learning_activities a "
        "JOIN learning_sessions s ON s.id=a.session_id JOIN courses c ON c.id=s.course_id "
        "WHERE s.user_id=? AND s.id<>? AND a.kind<>'lesson'",
        (row["user_id"], row["id"]),
    ):
        prior_spec = json.loads(previous["content"]).get("readiness", {})
        obj = next(
            (
                o
                for o in prior_spec.get("objectives", [])
                if o["id"] == previous["objective_id"]
            ),
            None,
        )
        question = _question(obj, previous["activity_id"]) if obj else None
        if question:
            exposed.add(question["prompt"].strip().casefold())
    records = [
        dict(r)
        for r in c.execute(
            "SELECT * FROM learning_activities WHERE session_id=? ORDER BY id",
            (row["id"],),
        )
    ]
    objectives, eligible = [], []
    for obj in spec["objectives"]:
        history = [r for r in records if r["objective_id"] == obj["id"]]
        submitted = [r for r in history if r["submitted"] is not None]
        diagnostic = next((r for r in submitted if r["kind"] == "diagnostic"), None)
        assessed = [r for r in submitted if r["kind"] == "reassessment"]
        passed = bool(assessed and assessed[-1]["correct"]) or obj["id"] in inherited
        pending_objective = any(r["submitted"] is None for r in history)
        available = [
            q
            for q in obj["reassessments"]
            if q["id"] not in {r["activity_id"] for r in history}
            and q["prompt"].strip().casefold() not in exposed
        ]
        exhausted = (
            not passed
            and not pending_objective
            and (len(assessed) >= spec["max_rounds"] or not available)
        )
        item = {
            "id": obj["id"],
            "title": obj["title"],
            "critical": obj["critical"],
            "source_section": obj["source_section"],
            "demonstrated": passed,
            "diagnostic_correct": bool(diagnostic["correct"]) if diagnostic else None,
            "reassessment_count": len(assessed),
            "needs_trainer": exhausted,
            "carried_from_session": inherited.get(obj["id"], {}).get("from_session_id"),
            "refresh_required": obj["id"] in refreshes,
            "evidence": [
                {
                    "activity_id": r["activity_id"],
                    "kind": r["kind"],
                    "correct": bool(r["correct"]) if r["correct"] is not None else None,
                    "submitted": r["submitted"],
                }
                for r in submitted
            ],
        }
        objectives.append(item)
        if passed or pending_objective or exhausted:
            continue
        if not diagnostic and obj["id"] not in refreshes:
            eligible.append(
                {
                    "objective_id": obj["id"],
                    "activity_id": obj["diagnostic"]["id"],
                    "kind": "diagnostic",
                    "reason": "Check your starting understanding of " + obj["title"],
                }
            )
        elif not passed and not exhausted:
            round_number = len(assessed)
            needs_lesson = (
                obj["id"] in refreshes or not diagnostic["correct"] or bool(assessed)
            )
            lesson_id = obj["id"] + "_lesson_" + str(round_number)
            if needs_lesson and not any(
                r["activity_id"] == lesson_id for r in submitted
            ):
                eligible.append(
                    {
                        "objective_id": obj["id"],
                        "activity_id": lesson_id,
                        "kind": "lesson",
                        "reason": (
                            "Review the changed procedure: "
                            if obj["id"] in refreshes
                            else "Review the missed step: "
                        )
                        + obj["title"],
                    }
                )
            else:
                q = available[0]
                eligible.append(
                    {
                        "objective_id": obj["id"],
                        "activity_id": q["id"],
                        "kind": "reassessment",
                        "reason": "Apply " + obj["title"] + " in a fresh case",
                    }
                )
    # Finish diagnosis before coaching. Activities are only exposed when issued.
    if any(x["kind"] == "diagnostic" for x in eligible):
        eligible = [x for x in eligible if x["kind"] == "diagnostic"]
    score = round(100 * sum(x["demonstrated"] for x in objectives) / len(objectives), 1)
    ready = score >= spec["threshold"] and all(
        x["demonstrated"] for x in objectives if x["critical"]
    )
    blocked = not row["approved"] or row["course_status"] != "published"
    pending = next((r for r in records if r["submitted"] is None), None)
    state = (
        "ready"
        if ready
        else (
            "diagnosing"
            if any(x["kind"] == "diagnostic" for x in eligible)
            else "practicing"
        )
    )
    if pending and pending["kind"] == "diagnostic":
        state = "diagnosing"
    if not ready and not eligible and not pending:
        state = "needs_trainer"
    if blocked:
        state = "blocked"
    if successor:
        state = "superseded"
    if ready or blocked or successor:
        eligible = []
    activity = None
    if pending and not blocked and not successor:
        obj = next(o for o in spec["objectives"] if o["id"] == pending["objective_id"])
        activity = {
            "id": pending["id"],
            "activity_id": pending["activity_id"],
            "objective_id": obj["id"],
            "title": obj["title"],
            "kind": pending["kind"],
            "source_section": obj["source_section"],
        }
        if pending["kind"] == "lesson":
            activity["text"] = obj["lesson"]
        else:
            q = _question(obj, pending["activity_id"])
            activity.update(prompt=q["prompt"], options=q["options"])
    reviews = [
        dict(r)
        for r in c.execute(
            "SELECT * FROM learning_reviews WHERE session_id=? ORDER BY id",
            (row["id"],),
        )
    ]
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "course_id": row["course_id"],
        "document_id": row["document_id"],
        "source_title": row["source_title"],
        "title": row["title"],
        "rule_version": row["rule_version"],
        "state": state,
        "superseded_by_course": successor[0] if successor else None,
        "score": score,
        "threshold": spec["threshold"],
        "objectives": objectives,
        "eligible_actions": eligible,
        "activity": activity,
        "reviews": reviews,
        "decisions": [
            json.loads(r["detail"])
            | {
                "issued_id": r["id"],
                "created": r["created"],
                "submitted": r["submitted"],
                "correct": bool(r["correct"]) if r["correct"] is not None else None,
            }
            for r in c.execute(
                "SELECT a.*,d.detail FROM learning_decisions d JOIN learning_activities a "
                "ON a.id=d.activity_id WHERE a.session_id=? ORDER BY a.id",
                (row["id"],),
            )
        ],
    }


def get(user, sid):
    with db.connect() as c:
        row, spec = _load(c, user, sid, trainer_read=True)
        return _view(c, row, spec)


def list_sessions(user):
    with db.connect() as c:
        rows = c.execute(
            "SELECT id FROM learning_sessions"
            + ("" if user["role"] == "trainer" else " WHERE user_id=?"),
            () if user["role"] == "trainer" else (user["id"],),
        ).fetchall()
        return [_view(c, *_load(c, user, r["id"], trainer_read=True)) for r in rows]


def start(user, course_id):
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        from src.workflows.change_impact import superseded

        if superseded(c, course_id):
            raise ValueError("This procedure was superseded; open the current course")
        course = c.execute(
            "SELECT c.* FROM courses c JOIN documents d ON d.id=c.document_id "
            "WHERE c.id=? AND c.status='published' AND d.approved=1",
            (course_id,),
        ).fetchone()
        if not course or "readiness" not in json.loads(course["content"]):
            raise ValueError("Choose an approved readiness course")
        spec = json.loads(course["content"])["readiness"]
        c.execute(
            "INSERT OR IGNORE INTO learning_sessions(user_id,course_id,document_id,rule_version,created) VALUES(?,?,?,?,?)",
            (
                user["id"],
                course_id,
                course["document_id"],
                spec["rule_version"],
                time.time(),
            ),
        )
        sid = c.execute(
            "SELECT id FROM learning_sessions WHERE user_id=? AND course_id=?",
            (user["id"], course_id),
        ).fetchone()[0]
        view = _view(c, *_load(c, user, sid))
        for objective in view["objectives"]:
            if objective["needs_trainer"]:
                c.execute(
                    "INSERT OR IGNORE INTO learning_reviews(session_id,reason,created) VALUES(?,?,?)",
                    (
                        sid,
                        "Fresh cases exhausted for " + objective["title"],
                        time.time(),
                    ),
                )
        return _view(c, *_load(c, user, sid))


def issue(user, sid, activity_id=None, selection_mode="backend"):
    if selection_mode not in {"gateway", "demo", "backend"}:
        raise ValueError("Unknown selection mode")
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row, spec = _load(c, user, sid)
        view = _view(c, row, spec)
        if view["state"] in ("blocked", "superseded"):
            raise ValueError("The source or course was withdrawn or superseded")
        if view["activity"]:
            return view
        choices = view["eligible_actions"]
        choice = (
            next((x for x in choices if x["activity_id"] == activity_id), None)
            if activity_id
            else next(iter(choices), None)
        )
        if not choice:
            raise ValueError("No eligible activity; refresh your learning state")
        issued = c.execute(
            "INSERT INTO learning_activities(session_id,objective_id,activity_id,kind,created) VALUES(?,?,?,?,?)",
            (
                sid,
                choice["objective_id"],
                choice["activity_id"],
                choice["kind"],
                time.time(),
            ),
        )
        objective = next(
            o for o in view["objectives"] if o["id"] == choice["objective_id"]
        )
        detail = {
            "mode": selection_mode,
            "kind": choice["kind"],
            "reason": choice["reason"],
            "objective_id": objective["id"],
            "objective_title": objective["title"],
            "critical": objective["critical"],
            "diagnostic_correct": objective["diagnostic_correct"],
            "reassessment_count": objective["reassessment_count"],
            "refresh_required": objective["refresh_required"],
            "source_title": row["source_title"],
            "source_section": objective["source_section"],
            "rule_version": row["rule_version"],
            "eligible_count": len(choices),
        }
        c.execute(
            "INSERT INTO learning_decisions(activity_id,detail) VALUES(?,?)",
            (issued.lastrowid, json.dumps(detail)),
        )
        db.event(
            c, user["id"], "issue_learning_activity", {"session_id": sid, **choice}
        )
        return _view(c, row, spec)


def submit(user, sid, issued_id, answer=None):
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row, spec = _load(c, user, sid)
        from src.workflows.change_impact import superseded

        if (
            not row["approved"]
            or row["course_status"] != "published"
            or superseded(c, row["course_id"])
        ):
            raise ValueError("The source or course was withdrawn or superseded")
        activity = c.execute(
            "SELECT * FROM learning_activities WHERE id=? AND session_id=?",
            (issued_id, sid),
        ).fetchone()
        if not activity:
            raise ValueError("Unknown issued activity")
        obj = next(o for o in spec["objectives"] if o["id"] == activity["objective_id"])
        if activity["kind"] == "lesson":
            if answer is not None:
                raise ValueError("Lessons do not accept scored answers")
            correct, feedback = None, "Lesson reviewed. Apply the step in a fresh case."
        else:
            q = _question(obj, activity["activity_id"])
            if type(answer) is not int or not 0 <= answer < len(q["options"]):
                raise ValueError("Select a valid answer")
            correct, feedback = int(answer == q["answer"]), q["explanation"]
        if activity["submitted"] is not None:
            if activity["answer"] != answer:
                raise ValueError("An already submitted answer cannot be changed")
        else:
            c.execute(
                "UPDATE learning_activities SET answer=?,correct=?,submitted=? WHERE id=?",
                (answer, correct, time.time(), issued_id),
            )
            db.event(
                c,
                user["id"],
                "record_learning_evidence",
                {"session_id": sid, "activity_id": issued_id, "correct": correct},
            )
        view = _view(c, row, spec)
        for objective in view["objectives"]:
            if objective["needs_trainer"]:
                c.execute(
                    "INSERT OR IGNORE INTO learning_reviews(session_id,reason,created) VALUES(?,?,?)",
                    (
                        sid,
                        "Fresh cases exhausted for " + objective["title"],
                        time.time(),
                    ),
                )
        return {
            "session": _view(c, row, spec),
            "feedback": feedback,
            "correct": bool(correct) if correct is not None else None,
        }


def request_review(user, sid, reason):
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 2000:
        raise ValueError("Provide a review question under 2,000 characters")
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row, spec = _load(c, user, sid)
        c.execute(
            "INSERT OR IGNORE INTO learning_reviews(session_id,reason,created) VALUES(?,?,?)",
            (sid, reason.strip(), time.time()),
        )
        return _view(c, row, spec)


def resolve_review(user, review_id, resolution):
    db.require_trainer(user)
    if not isinstance(resolution, str) or not 1 <= len(resolution.strip()) <= 2000:
        raise ValueError("Provide trainer guidance under 2,000 characters")
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        review = c.execute(
            "SELECT * FROM learning_reviews WHERE id=?", (review_id,)
        ).fetchone()
        if not review:
            raise ValueError("Unknown review item")
        if review["status"] != "open":
            if review["resolution"] != resolution.strip():
                raise ValueError("This review already has a recorded resolution")
            return {"ok": True}
        c.execute(
            "UPDATE learning_reviews SET status='resolved',resolution=?,resolved=? WHERE id=?",
            (resolution.strip(), time.time(), review_id),
        )
        db.event(c, user["id"], "resolve_learning_review", {"review_id": review_id})
        return {"ok": True}
