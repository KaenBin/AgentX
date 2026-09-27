"""Trainer-approved procedure revisions and evidence-preserving refresh assignments."""

import copy
import difflib
import hashlib
import json
import time
from src.tools import db_queries as db
from src.workflows.chain import validate_course
from src.workflows.readiness_content import validate_readiness


def migrate(c):
    for sql in [
        """CREATE TABLE IF NOT EXISTS procedure_revisions(
        id INTEGER PRIMARY KEY,old_course_id INTEGER NOT NULL REFERENCES courses(id),
        new_course_id INTEGER UNIQUE NOT NULL REFERENCES courses(id),root_course_id INTEGER NOT NULL,
        version INTEGER NOT NULL,base_hash TEXT NOT NULL,target_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',affected TEXT,equivalent TEXT,
        created_by INTEGER NOT NULL REFERENCES users(id),approved_by INTEGER REFERENCES users(id),
        created REAL NOT NULL,activated REAL)""",
        """CREATE TABLE IF NOT EXISTS procedure_successors(
        old_course_id INTEGER PRIMARY KEY REFERENCES courses(id),
        new_course_id INTEGER UNIQUE NOT NULL REFERENCES courses(id),
        revision_id INTEGER UNIQUE NOT NULL REFERENCES procedure_revisions(id))""",
        """CREATE TABLE IF NOT EXISTS learning_carryovers(
        session_id INTEGER NOT NULL REFERENCES learning_sessions(id),objective_id TEXT NOT NULL,
        from_session_id INTEGER NOT NULL REFERENCES learning_sessions(id),
        revision_id INTEGER NOT NULL REFERENCES procedure_revisions(id),
        PRIMARY KEY(session_id,objective_id))""",
        """CREATE TABLE IF NOT EXISTS learning_refreshes(
        session_id INTEGER NOT NULL REFERENCES learning_sessions(id),objective_id TEXT NOT NULL,
        revision_id INTEGER NOT NULL REFERENCES procedure_revisions(id),
        PRIMARY KEY(session_id,objective_id))""",
    ]:
        c.execute(sql)
    c.execute("INSERT OR IGNORE INTO readiness_migrations VALUES(2)")


def course_row(c, cid):
    row = c.execute(
        "SELECT c.*,d.body,d.title source_title,d.approved FROM courses c "
        "JOIN documents d ON d.id=c.document_id WHERE c.id=?",
        (cid,),
    ).fetchone()
    if not row or "readiness" not in json.loads(row["content"]):
        raise ValueError("Choose a readiness course")
    return row


def fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            [
                row["title"],
                row["document_id"],
                row["source_title"],
                row["body"],
                json.loads(row["content"]),
            ],
            sort_keys=True,
        ).encode()
    ).hexdigest()


def superseded(c, cid):
    return c.execute(
        "SELECT new_course_id FROM procedure_successors WHERE old_course_id=?", (cid,)
    ).fetchone()


def managed_document(c, did):
    return c.execute(
        "SELECT r.id FROM procedure_revisions r JOIN courses n ON n.id=r.new_course_id "
        "JOIN courses o ON o.id=r.old_course_id WHERE (n.document_id=? AND r.status='draft') "
        "OR (o.document_id=? AND r.status='activated')",
        (did, did),
    ).fetchone()


def compare(old, new):
    before, after = (
        json.loads(old["content"])["readiness"],
        json.loads(new["content"])["readiness"],
    )
    old_objs = {o["id"]: o for o in before["objectives"]}
    old_sections, new_sections = db.sections(old["body"]), db.sections(new["body"])
    rules_changed = any(
        before[k] != after[k] for k in ["rule_version", "threshold", "max_rounds"]
    )
    items = []
    for obj in after["objectives"]:
        prior = old_objs.get(obj["id"])
        old_text = old_sections[prior["source_section"] - 1] if prior else ""
        new_text = new_sections[obj["source_section"] - 1]
        changed = not prior or prior != obj or old_text != new_text or rules_changed
        items.append(
            {
                "id": obj["id"],
                "title": obj["title"],
                "required_refresh": bool(changed),
                "old_source": old_text,
                "new_source": new_text,
                "reason": (
                    "New objective or changed content, source or completion rule"
                    if changed
                    else "Identical objective and supporting source"
                ),
            }
        )
    return {
        "objectives": items,
        "removed_objectives": [
            o["id"]
            for o in before["objectives"]
            if o["id"] not in {n["id"] for n in after["objectives"]}
        ],
        "diff": "\n".join(
            difflib.unified_diff(
                old["body"].splitlines(),
                new["body"].splitlines(),
                fromfile=old["source_title"],
                tofile=new["source_title"],
                lineterm="",
            )
        ),
    }


def _detail(c, revision):
    old, new = course_row(c, revision["old_course_id"]), course_row(
        c, revision["new_course_id"]
    )
    return dict(revision) | {
        "old_title": old["title"],
        "old_document_id": old["document_id"],
        "new_document_id": new["document_id"],
        "can_activate": bool(
            old["approved"]
            and old["status"] == "published"
            and not superseded(c, old["id"])
        ),
        "new_title": new["title"],
        "new_source": new["body"],
        "new_content": json.loads(new["content"]),
        "comparison": compare(old, new),
        "learner_count": c.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE course_id=?", (old["id"],)
        ).fetchone()[0],
    }


def list_revisions(user):
    if user["role"] != "trainer":
        return []
    with db.connect() as c:
        return [
            _detail(c, r)
            for r in c.execute(
                "SELECT * FROM procedure_revisions ORDER BY id DESC"
            ).fetchall()
        ]


def create(user, old_course_id, title, body, content):
    db.require_trainer(user)
    if (
        not isinstance(title, str)
        or not 1 <= len(title.strip()) <= 180
        or not isinstance(body, str)
        or not 40 <= len(body) <= 100000
    ):
        raise ValueError(
            "Provide a title and a source between 40 and 100,000 characters"
        )
    validate_course(content)
    if "readiness" not in content:
        raise ValueError(
            "The revision needs approved-style readiness content for review"
        )
    validate_readiness(content, len(db.sections(body)))
    if any(
        not 1 <= l["source_section"] <= len(db.sections(body))
        for l in content["lessons"]
    ):
        raise ValueError("Invalid lesson source reference")
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        old = course_row(c, old_course_id)
        if (
            not old["approved"]
            or old["status"] != "published"
            or superseded(c, old_course_id)
        ):
            raise ValueError("Revise the current approved course")
        previous = c.execute(
            "SELECT root_course_id,version FROM procedure_revisions WHERE new_course_id=? AND status='activated'",
            (old_course_id,),
        ).fetchone()
        did = c.execute(
            "INSERT INTO documents(title,body,created) VALUES(?,?,?)",
            (title.strip(), body, time.time()),
        ).lastrowid
        cid = c.execute(
            "INSERT INTO courses(title,document_id,content) VALUES(?,?,?)",
            (title.strip(), did, json.dumps(content)),
        ).lastrowid
        new = course_row(c, cid)
        rid = c.execute(
            "INSERT INTO procedure_revisions(old_course_id,new_course_id,root_course_id,version,base_hash,target_hash,created_by,created) VALUES(?,?,?,?,?,?,?,?)",
            (
                old_course_id,
                cid,
                previous["root_course_id"] if previous else old_course_id,
                previous["version"] + 1 if previous else 2,
                fingerprint(old),
                fingerprint(new),
                user["id"],
                time.time(),
            ),
        ).lastrowid
        db.event(c, user["id"], "draft_procedure_revision", {"revision_id": rid})
        return _detail(
            c,
            c.execute(
                "SELECT * FROM procedure_revisions WHERE id=?", (rid,)
            ).fetchone(),
        )


def activate(user, revision_id, affected_ids, equivalent_ids):
    from src.workflows import readiness

    db.require_trainer(user)
    with db.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        revision = c.execute(
            "SELECT * FROM procedure_revisions WHERE id=?", (revision_id,)
        ).fetchone()
        if not revision:
            raise ValueError("Unknown revision")
        affected, equivalent = set(affected_ids), set(equivalent_ids)
        if len(affected) != len(affected_ids) or len(equivalent) != len(equivalent_ids):
            raise ValueError("Objective IDs must be unique")
        if revision["status"] == "activated":
            if affected != set(json.loads(revision["affected"])) or equivalent != set(
                json.loads(revision["equivalent"])
            ):
                raise ValueError(
                    "This revision was already activated with a different mapping"
                )
            return {
                "ok": True,
                "new_course_id": revision["new_course_id"],
                "already_activated": True,
            }
        old, new = course_row(c, revision["old_course_id"]), course_row(
            c, revision["new_course_id"]
        )
        if (
            superseded(c, old["id"])
            or not old["approved"]
            or old["status"] != "published"
        ):
            raise ValueError("The base version is no longer current and approved")
        if (
            fingerprint(old) != revision["base_hash"]
            or fingerprint(new) != revision["target_hash"]
        ):
            raise ValueError(
                "Content changed after comparison; create a new revision for review"
            )
        if new["status"] != "draft" or new["approved"]:
            raise ValueError("Activate the untouched draft through the revision review")
        comparison = compare(old, new)
        ids = {o["id"] for o in comparison["objectives"]}
        required = {o["id"] for o in comparison["objectives"] if o["required_refresh"]}
        if (
            affected & equivalent
            or affected | equivalent != ids
            or not required <= affected
        ):
            raise ValueError(
                "Every objective needs a mapping; changed objectives require fresh practice"
            )
        old_spec = json.loads(old["content"])["readiness"]
        new_spec = json.loads(new["content"])["readiness"]
        old_prompts = {
            q["prompt"].strip().casefold()
            for o in old_spec["objectives"]
            for q in [o["diagnostic"], *o["reassessments"]]
        }
        for obj in new_spec["objectives"]:
            if obj["id"] in affected and any(
                q["prompt"].strip().casefold() in old_prompts
                for q in obj["reassessments"]
            ):
                raise ValueError(
                    "Refresh objectives need new reassessment prompts, not reused cases"
                )
        if c.execute(
            "SELECT 1 FROM learning_sessions WHERE course_id=?", (new["id"],)
        ).fetchone():
            raise ValueError("The target already has learning records")
        old_sessions = c.execute(
            "SELECT * FROM learning_sessions WHERE course_id=?", (old["id"],)
        ).fetchall()
        for prior in old_sessions:
            learner = {"id": prior["user_id"], "role": "learner"}
            view = readiness._view(c, *readiness._load(c, learner, prior["id"]))
            new_sid = c.execute(
                "INSERT INTO learning_sessions(user_id,course_id,document_id,rule_version,created) VALUES(?,?,?,?,?)",
                (
                    prior["user_id"],
                    new["id"],
                    new["document_id"],
                    new_spec["rule_version"],
                    time.time(),
                ),
            ).lastrowid
            for obj in view["objectives"]:
                if obj["id"] in equivalent and obj["demonstrated"]:
                    c.execute(
                        "INSERT INTO learning_carryovers VALUES(?,?,?,?)",
                        (new_sid, obj["id"], prior["id"], revision_id),
                    )
            for oid in affected:
                c.execute(
                    "INSERT INTO learning_refreshes VALUES(?,?,?)",
                    (new_sid, oid, revision_id),
                )
        c.execute("UPDATE documents SET approved=1 WHERE id=?", (new["document_id"],))
        c.execute("UPDATE courses SET status='published' WHERE id=?", (new["id"],))
        c.execute(
            "INSERT INTO procedure_successors VALUES(?,?,?)",
            (old["id"], new["id"], revision_id),
        )
        # Stop all courses and retrieval against the obsolete source.
        c.execute("UPDATE documents SET approved=0 WHERE id=?", (old["document_id"],))
        c.execute(
            "UPDATE procedure_revisions SET status='activated',affected=?,equivalent=?,approved_by=?,activated=? WHERE id=?",
            (
                json.dumps(sorted(affected)),
                json.dumps(sorted(equivalent)),
                user["id"],
                time.time(),
                revision_id,
            ),
        )
        for session in c.execute(
            "SELECT id,user_id FROM learning_sessions WHERE course_id=?", (new["id"],)
        ).fetchall():
            view = readiness._view(
                c,
                *readiness._load(
                    c, {"id": session["user_id"], "role": "learner"}, session["id"]
                ),
            )
            for obj in view["objectives"]:
                if obj["needs_trainer"]:
                    c.execute(
                        "INSERT OR IGNORE INTO learning_reviews(session_id,reason,created) VALUES(?,?,?)",
                        (
                            session["id"],
                            "Fresh cases exhausted for " + obj["title"],
                            time.time(),
                        ),
                    )
        db.event(
            c,
            user["id"],
            "activate_procedure_revision",
            {
                "revision_id": revision_id,
                "affected": sorted(affected),
                "equivalent": sorted(equivalent),
                "assigned": len(old_sessions),
            },
        )
        return {"ok": True, "new_course_id": new["id"], "assigned": len(old_sessions)}


def fictional_update(user, cid):
    """Prepare, never approve, a narrowly defined fictional receipt-rule update."""
    db.require_trainer(user)
    with db.connect() as c:
        row = course_row(c, cid)
        content = copy.deepcopy(json.loads(row["content"]))
        body = row["body"]
    old_sentence = "If a receipt is missing, request a duplicate from the supplier before submitting the claim."
    if old_sentence not in body or "fictional" not in row["source_title"].lower():
        raise ValueError(
            "The demo update requires the original fictional receipt policy"
        )
    replacement = "If a receipt is missing, first request a duplicate from the supplier. If the supplier cannot provide one, obtain a written Finance exception before submitting the claim."
    original_requirement = "Every reimbursement claim must include an itemized receipt."
    updated_requirement = "Every reimbursement claim must include an itemized receipt or a written Finance exception under the rule below."

    def update_text(text):
        return text.replace(old_sentence, replacement).replace(
            original_requirement, updated_requirement
        )

    body = update_text(body)
    obj = next(
        (
            o
            for o in content["readiness"]["objectives"]
            if o["id"] == "receipt_evidence"
        ),
        None,
    )
    if obj is None:
        raise ValueError("The demo update requires the receipt objective")
    obj["lesson"] = update_text(obj["lesson"])
    for lesson in content["lessons"]:
        lesson["text"] = update_text(lesson["text"])
    for bank in ["questions", "assessment_questions"]:
        for q in content[bank]:
            q["explanation"] = update_text(q["explanation"])
    obj["diagnostic"]["explanation"] = obj["lesson"]
    obj["diagnostic"].update(
        prompt="A lost receipt can be replaced by the supplier. What should the employee obtain first?",
        options=[
            "A duplicate itemized receipt",
            "Only a bank statement",
            "A verbal description",
        ],
        answer=0,
    )
    for i, prompt in enumerate(
        [
            "Version 2: the restaurant cannot replace a lost receipt. What must happen before the employee submits the claim?",
            "Version 2: a taxi supplier confirms no duplicate is available. Which next action meets the updated evidence rule?",
        ]
    ):
        obj["reassessments"][i] = {
            "id": f"receipt_v2_case_{i+1}",
            "prompt": prompt,
            "options": [
                "Submit only the bank statement",
                "Obtain a written Finance exception before submission",
                "Assume the claim is automatically approved",
            ],
            "answer": 1,
            "explanation": obj["lesson"],
            "skill": 0,
        }
    return create(
        user, cid, "Expense procedure version 2 — fictional pilot", body, content
    )
