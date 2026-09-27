"""Allowlisted read tools bound to the authenticated learner."""

import json
from src.tools import db_queries as db
from src.agents.protocol import validate_tool


def execute(user, name, args):
    args = validate_tool(name, args)
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object")
    if name == "get_learning_state":
        from src.workflows.readiness import list_sessions
        return {"sessions": [s for s in list_sessions(user) if s["user_id"] == user["id"]]}
    if name == "select_approved_activity":
        from src.workflows.readiness import get
        session = get(user, args["session_id"])
        if session["user_id"] != user["id"]:
            raise ValueError("Choose your own learning session")
        choice = next((x for x in session["eligible_actions"] if x["activity_id"] == args["activity_id"]), None)
        if not choice:
            raise ValueError("Choose a currently eligible activity")
        return {"recommendation": choice, "session_id": session["id"]}
    if name == "get_my_progress":
        if args:
            raise ValueError("Progress takes no arguments")
        with db.connect() as c:
            courses = [
                dict(r)
                for r in c.execute(
                    "SELECT c.id,c.title FROM courses c JOIN documents d ON d.id=c.document_id WHERE status='published' AND approved=1"
                )
            ]
            attempts = [
                dict(r)
                for r in c.execute(
                    "SELECT course_id,phase,score,feedback FROM attempts WHERE user_id=? ORDER BY id DESC LIMIT 10",
                    (user["id"],),
                )
            ]
        for attempt in attempts:
            attempt["weak_skills"] = sorted(
                {
                    f["skill"]
                    for f in json.loads(attempt.pop("feedback"))
                    if not f["correct"]
                }
            )
        from src.workflows.readiness import list_sessions
        return {"courses": courses, "attempts": attempts,
                "learning_sessions": [s for s in list_sessions(user) if s["user_id"] == user["id"]]}
    if name == "retrieve_sources":
        if (
            set(args) != {"query"}
            or not isinstance(args["query"], str)
            or not 1 <= len(args["query"].strip()) <= 2000
        ):
            raise ValueError("Provide a search query")
        terms = db.tokens(args["query"])
        hits = []
        with db.connect() as c:
            for doc in c.execute("SELECT * FROM documents WHERE approved=1"):
                for index, text in enumerate(db.sections(doc["body"])):
                    score = len(terms & db.tokens(text)) / max(len(terms), 1)
                    if score >= 0.25:
                        hits.append(
                            {
                                "document_id": doc["id"],
                                "title": doc["title"],
                                "section": index + 1,
                                "excerpt": text,
                                "score": score,
                            }
                        )
        return {"sources": sorted(hits, key=lambda s: s["score"], reverse=True)[:3]}
    if name == "get_course_outline":
        with db.connect() as c:
            row = c.execute(
                "SELECT c.* FROM courses c JOIN documents d ON d.id=c.document_id "
                "WHERE c.id=? AND c.status='published' AND d.approved=1",
                (args["course_id"],),
            ).fetchone()
        if not row:
            raise ValueError("Course is no longer available")
        return {
            "course_id": row["id"],
            "title": row["title"],
            "lessons": [
                {"skill": i, "title": lesson["title"]}
                for i, lesson in enumerate(json.loads(row["content"])["lessons"])
            ],
        }
    if name == "recommend_lesson":
        if set(args) != {"course_id", "skill"} or any(
            type(v) is not int for v in args.values()
        ):
            raise ValueError("Provide a course and skill")
        with db.connect() as c:
            row = c.execute(
                "SELECT c.*,d.title source_title FROM courses c JOIN documents d ON d.id=c.document_id WHERE c.id=? AND status='published' AND approved=1",
                (args["course_id"],),
            ).fetchone()
        if not row:
            raise ValueError("Course is no longer available")
        lessons = json.loads(row["content"])["lessons"]
        if not 0 <= args["skill"] < len(lessons):
            raise ValueError("Unknown lesson")
        lesson = lessons[args["skill"]]
        return {
            "lesson": lesson,
            "sources": [
                {
                    "document_id": row["document_id"],
                    "title": row["source_title"],
                    "section": lesson["source_section"],
                    "excerpt": lesson["text"],
                }
            ],
        }
    raise ValueError("Tool is not allowed")
