"""Shared pytest fixtures."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.config import LLMProvider, Settings
from core.llm import MockLLMClient
from tools.base import ToolRegistry
from tools.db_queries import DatabaseQueryTool
from tools.file_ops import ReadFileTool, WriteFileTool


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    sandbox = tmp_path / "sandbox"
    db_path = sandbox / "sme.db"
    return Settings(
        llm_provider=LLMProvider.MOCK,
        sandbox_root=sandbox,
        database_url=f"sqlite:///{db_path}",
        max_agent_steps=5,
    )


@pytest.fixture
def sme_db(settings: Settings) -> str:
    """Create a small SME database (customers + invoices) and return its path."""
    db_path = settings.database_url.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, paid INTEGER
        );
        INSERT INTO customers (id, name, city) VALUES
            (1, 'Ah Seng Trading', 'Singapore'),
            (2, 'Merlion Cafe', 'Singapore');
        INSERT INTO invoices (id, customer_id, amount, paid) VALUES
            (1, 1, 1200.50, 0),
            (2, 2, 340.00, 1);
        """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient(
        canned={
            "produce the numbered plan": (
                "1. Gather the outstanding invoices\n2. Draft the reminder"
            ),
            "final answer": "Here is your ready-to-use reminder.",
        }
    )


@pytest.fixture
def registry(settings: Settings, sme_db: str) -> ToolRegistry:
    return ToolRegistry(
        [
            ReadFileTool(settings.sandbox_root),
            WriteFileTool(settings.sandbox_root),
            DatabaseQueryTool(settings.database_url),
        ]
    )
