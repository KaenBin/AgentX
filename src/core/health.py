"""Read-only readiness checks for the deployed main database."""

from contextlib import closing
import sqlite3

from src.tools import db_queries as db


REQUIRED_TABLES = (
    "users", "sessions", "documents", "courses", "attempts", "chats", "events",
    "readiness_migrations", "learning_sessions", "learning_activities",
    "learning_reviews", "learning_decisions", "procedure_revisions",
    "procedure_successors", "learning_carryovers", "learning_refreshes",
)


def database_ready() -> bool:
    """Read the main database with a one-second lock wait and no file creation."""
    try:
        uri = db.DB.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=1)) as connection:
            connection.execute("SELECT 1 FROM users LIMIT 1").fetchone()
            placeholders = ",".join("?" for _ in REQUIRED_TABLES)
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    f"AND name IN ({placeholders})", REQUIRED_TABLES
                )
            }
            return tables == set(REQUIRED_TABLES)
    except (OSError, sqlite3.Error):
        return False
