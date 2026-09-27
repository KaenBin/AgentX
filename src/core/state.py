"""Application state returned to the authenticated user; answer keys stay private."""

import json
from dataclasses import dataclass, field
from typing import TypedDict
from src.core.config import Settings
from src.tools.db_queries import connect


class User(TypedDict):
    id: int
    name: str
    role: str


@dataclass
class AgentState:
    question: str
    sources: list[dict] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


def snapshot(u):
    with connect() as c:
        docs = [
            dict(x)
            for x in c.execute(
                "SELECT * FROM documents"
                + ("" if u["role"] == "trainer" else " WHERE approved=1")
            )
        ]
        courses = []
        for r in c.execute(
            "SELECT c.*,d.approved FROM courses c JOIN documents d ON d.id=c.document_id"
        ):
            if u["role"] != "trainer" and (
                r["status"] != "published" or not r["approved"]
            ):
                continue
            x = dict(r)
            x["content"] = json.loads(x["content"])
            if u["role"] != "trainer":
                if "readiness" in x["content"]:
                    spec = x["content"]["readiness"]
                    x["content"]["readiness"] = {
                        "rule_version": spec["rule_version"],
                        "threshold": spec["threshold"],
                        "objectives": [{k: o[k] for k in ("id", "title", "critical", "source_section")} for o in spec["objectives"]],
                    }
                    # Fresh cases are delivered only as issued activities.
                    x["content"]["questions"] = []
                    x["content"]["assessment_questions"] = []
                for q in x["content"]["questions"] + x["content"].get(
                    "assessment_questions", []
                ):
                    q.pop("answer", None)
                    q.pop("explanation", None)
            courses.append(x)
        sql = "SELECT a.*,u.name FROM attempts a JOIN users u ON u.id=a.user_id"
        args = ()
        if u["role"] != "trainer":
            sql += " WHERE user_id=?"
            args = (u["id"],)
        attempts = [dict(x) for x in c.execute(sql + " ORDER BY a.id DESC", args)]
        for a in attempts:
            a["feedback"] = json.loads(a["feedback"])
            a.pop("answers")
        events = (
            [
                dict(x)
                for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 25")
            ]
            if u["role"] == "trainer"
            else []
        )
        chats = [
            json.loads(r["response"])
            | {"question": r["question"], "created": r["created"]}
            for r in c.execute(
                "SELECT * FROM (SELECT * FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 30) ORDER BY id",
                (u["id"],),
            )
        ]
    from src.workflows.readiness import list_sessions
    from src.workflows.change_impact import list_revisions
    return {
        "procedure_revisions": list_revisions(u),
        "learning_sessions": list_sessions(u),
        "user": u,
        "documents": docs,
        "courses": courses,
        "attempts": attempts,
        "events": events,
        "mode": Settings().mode_label,
        "chats": chats,
    }
