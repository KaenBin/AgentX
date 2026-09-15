"""Unit tests for the tools package (sandboxing + read-only DB guard)."""

from __future__ import annotations

import pytest

from tools.base import ToolError, ToolRegistry
from tools.db_queries import DatabaseQueryTool
from tools.file_ops import ReadFileTool, WriteFileTool


def test_write_then_read_roundtrip(settings) -> None:
    writer = WriteFileTool(settings.sandbox_root)
    reader = ReadFileTool(settings.sandbox_root)
    writer.invoke({"path": "notes/hello.txt", "content": "hello SME"})
    assert reader.invoke({"path": "notes/hello.txt"}) == "hello SME"


def test_path_traversal_is_blocked(settings) -> None:
    writer = WriteFileTool(settings.sandbox_root)
    with pytest.raises(ToolError):
        writer.invoke({"path": "../escape.txt", "content": "nope"})


def test_read_missing_file_errors(settings) -> None:
    reader = ReadFileTool(settings.sandbox_root)
    with pytest.raises(ToolError):
        reader.invoke({"path": "does_not_exist.txt"})


def test_db_select_returns_rows(settings, sme_db) -> None:
    tool = DatabaseQueryTool(settings.database_url)
    rows = tool.invoke({"sql": "SELECT name FROM customers ORDER BY id"})
    assert rows[0]["name"] == "Ah Seng Trading"


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM invoices",
        "UPDATE invoices SET paid = 1",
        "DROP TABLE customers",
        "SELECT 1; DROP TABLE customers",
        "INSERT INTO customers (name) VALUES ('x')",
    ],
)
def test_db_rejects_writes(settings, sme_db, sql) -> None:
    tool = DatabaseQueryTool(settings.database_url)
    with pytest.raises(ToolError):
        tool.invoke({"sql": sql})


def test_registry_dispatch_and_unknown_tool(settings, sme_db) -> None:
    registry = ToolRegistry([DatabaseQueryTool(settings.database_url)])
    assert "db_query" in registry
    with pytest.raises(ToolError):
        registry.dispatch("nope", {})


def test_invalid_arguments_raise_toolerror(settings) -> None:
    reader = ReadFileTool(settings.sandbox_root)
    with pytest.raises(ToolError):
        reader.invoke({})  # missing required `path`
