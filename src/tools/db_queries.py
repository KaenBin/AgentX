"""AgentX Learn: local-first training workflow. Python standard library runtime."""

import json, sqlite3, hashlib, secrets, time, re, os
from pathlib import Path
from contextvars import ContextVar
from src.core.config import Settings
from src.workflows.chain import build_course

DB = Settings().database_path
DATABASE_OVERRIDE = ContextVar("demo_database", default=None)
STOP = set(
    "the a an is are can i my to for of in on and what how do does when should it this with we our must be".split()
)


def tokens(s):
    return set(re.findall(r"\w+", s.lower())) - STOP


from contextlib import contextmanager


@contextmanager
def connect():
    database = DATABASE_OVERRIDE.get() or DB
    database.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(database, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        with c:
            yield c
    finally:
        c.close()


def digest(p, s):
    return hashlib.pbkdf2_hmac("sha256", p.encode(), s.encode(), 180000).hex()


def init():
    with connect() as c:
        c.executescript(
            """CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,role TEXT,salt TEXT,password TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),expires REAL);
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,title TEXT,body TEXT,approved INTEGER DEFAULT 0,created REAL);
CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY,title TEXT,document_id INTEGER REFERENCES documents(id),content TEXT,status TEXT DEFAULT 'draft');
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),course_id INTEGER REFERENCES courses(id),phase TEXT,answers TEXT,score REAL,feedback TEXT,created REAL);
CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),question TEXT,response TEXT,created REAL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT,detail TEXT,created REAL);"""
        )
        if not c.execute("SELECT 1 FROM users").fetchone():
            for name, role in [
                ("trainer", "trainer"),
                ("learner", "learner"),
                ("alex", "learner"),
            ]:
                salt = secrets.token_hex(16)
                c.execute(
                    "INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)",
                    (name, role, salt, digest("LearnDemo2026!", salt)),
                )
            body = """Receipt evidence\nEvery reimbursement claim must include an itemized receipt. If a receipt is missing, request a duplicate from the supplier before submitting the claim. A bank statement alone is not sufficient.\n\nSubmission deadline\nSubmit expense claims within 30 calendar days of the purchase date. Late claims require manager review and are not automatically accepted.\n\nManager approval\nExpenses above SGD 200 require written manager approval before purchase. Attach that approval to the claim.\n\nClaim review\nFinance reviews complete claims within five business days. If information is missing, Finance returns the claim for correction. Do not submit the same expense twice."""
            cur = c.execute(
                "INSERT INTO documents(title,body,approved,created) VALUES(?,?,1,?)",
                ("Example expense policy v1 — fictional demo", body, time.time()),
            )
            from src.workflows.sample_course import add_banks

            course = add_banks(build_course("Expense reimbursement essentials", body))
            c.execute(
                "INSERT INTO courses(title,document_id,content,status) VALUES(?,?,?,?)",
                (
                    "Expense reimbursement essentials",
                    cur.lastrowid,
                    json.dumps(course),
                    "published",
                ),
            )
        # Preserve existing immutable courses and attempts; add a new curated version once.
        old = c.execute(
            "SELECT c.*,d.body FROM courses c JOIN documents d ON d.id=c.document_id WHERE d.title=? ORDER BY c.id LIMIT 1",
            ("Example expense policy v1 — fictional demo",),
        ).fetchone()
        if old and "assessment_questions" not in json.loads(old["content"]):
            title = "Expense reimbursement essentials v2"
            if not c.execute(
                "SELECT 1 FROM courses WHERE title=?", (title,)
            ).fetchone():
                from src.workflows.sample_course import add_banks

                content = add_banks(build_course(title, old["body"]))
                c.execute(
                    "INSERT INTO courses(title,document_id,content,status) VALUES(?,?,?,?)",
                    (title, old["document_id"], json.dumps(content), "published"),
                )
        from src.workflows.readiness import migrate
        from src.workflows.readiness_content import seed_pilot
        migrate(c)
        seed_pilot(c)


def event(c, uid, action, detail):
    c.execute(
        "INSERT INTO events(user_id,action,detail,created) VALUES(?,?,?,?)",
        (uid, action, json.dumps(detail), time.time()),
    )


def login(name, password):
    with connect() as c:
        u = c.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
        if not u or not secrets.compare_digest(
            u["password"], digest(password, u["salt"])
        ):
            raise ValueError("Incorrect username or password")
        t = secrets.token_urlsafe(32)
        c.execute(
            "INSERT INTO sessions VALUES(?,?,?)", (t, u["id"], time.time() + 28800)
        )
        return t


def user(token):
    with connect() as c:
        r = c.execute(
            "SELECT u.id,u.name,u.role FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?",
            (token, time.time()),
        ).fetchone()
        return dict(r) if r else None


def require_trainer(u):
    if u["role"] != "trainer":
        raise PermissionError("Trainer access required")


def sections(body):
    return [x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()]


def logout(token):
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))
