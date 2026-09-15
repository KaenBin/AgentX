"""Read-only database query tool.

SME data (invoices, customers, inventory) usually lives in a small SQL store.
This tool exposes it to an agent as a *read-only* interface: only ``SELECT``
statements are permitted and results are capped, so an agent can answer
questions and build reports without any risk of mutating business data.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from tools.base import Tool, ToolError

# Statements that must never be reachable through this tool.
_FORBIDDEN = re.compile(
    r"(?i)\b(insert|update|delete|drop|alter|create|replace|truncate|attach|pragma)\b"
)


class DatabaseQueryArgs(BaseModel):
    sql: str = Field(description="A single read-only SELECT statement.")
    max_rows: int = Field(default=100, ge=1, le=10_000)


def _sqlite_path_from_url(database_url: str) -> str:
    """Extract a filesystem path from a ``sqlite:///path`` URL (or return as-is)."""
    if database_url.startswith("sqlite:///"):
        return database_url[len("sqlite:///") :]
    if database_url.startswith("sqlite://"):
        return database_url[len("sqlite://") :]
    return database_url


class DatabaseQueryTool(Tool):
    name = "db_query"
    description = "Run a read-only SQL SELECT against the SME database and return rows."
    args_schema = DatabaseQueryArgs

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._db_path = _sqlite_path_from_url(database_url)

    @staticmethod
    def _assert_read_only(sql: str) -> str:
        stripped = sql.strip().rstrip(";").strip()
        if ";" in stripped:
            raise ToolError("Only a single statement is allowed (no ';' separators).")
        if not stripped.lower().startswith(("select", "with")):
            raise ToolError("Only SELECT/WITH queries are permitted.")
        if _FORBIDDEN.search(stripped):
            raise ToolError("Query contains a forbidden (write/DDL) keyword.")
        return stripped

    def run(self, sql: str, max_rows: int = 100) -> list[dict[str, Any]]:  # type: ignore[override]
        query = self._assert_read_only(sql)
        db_file = Path(self._db_path)
        if not db_file.exists():
            raise ToolError(f"Database not found at {self._db_path!r}")

        # Open read-only via URI so the connection itself cannot write.
        uri = f"file:{db_file}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            rows = cursor.fetchmany(max_rows)
            return [dict(row) for row in rows]
