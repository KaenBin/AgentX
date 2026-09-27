"""Isolated fictional rehearsals; request-local database and model mode."""

import re
import secrets
import sqlite3
from dataclasses import replace

from src.core.config import Settings, MODE_OVERRIDE
from src.tools import db_queries as db


def location(token):
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Invalid rehearsal identifier")
    return db.DB.resolve().parent / "rehearsals" / (token + ".db")


def lookup(token):
    path = location(token)
    if not path.is_file():
        raise ValueError("Rehearsal is unavailable")
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT mode FROM rehearsal_context").fetchone()
    if not row or row[0] not in {"demo", "gateway"}:
        raise ValueError("Rehearsal configuration is invalid")
    return path, row[0]


def create(user, mode):
    db.require_trainer(user)
    replace(Settings(), mode=mode).validate()
    token = secrets.token_hex(16)
    path = location(token)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Refuse accidental collisions; never reuse or erase an existing rehearsal.
    with path.open("xb"):
        pass
    database_scope = db.DATABASE_OVERRIDE.set(path)
    mode_scope = MODE_OVERRIDE.set(mode)
    try:
        db.init()
        with db.connect() as connection:
            connection.execute("CREATE TABLE rehearsal_context(mode TEXT NOT NULL)")
            connection.execute("INSERT INTO rehearsal_context VALUES(?)", (mode,))
        session = db.login("learner", "LearnDemo2026!")
    finally:
        MODE_OVERRIDE.reset(mode_scope)
        db.DATABASE_OVERRIDE.reset(database_scope)
    return token, session
