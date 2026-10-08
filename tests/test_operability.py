"""Deployment probes and privacy-safe request diagnostics."""

import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.tools import db_queries as db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Run the app against a fresh fictional database."""
    monkeypatch.setattr(db, "DB", tmp_path / "main.db")
    with TestClient(app) as client:
        yield client


def test_ready_checks_initialized_database_without_model_calls(client, monkeypatch):
    """Readiness reports the deployed app while liveness keeps its existing shape."""
    def no_model(*args, **kwargs):
        raise AssertionError("A readiness probe must not call the gateway")

    monkeypatch.setattr("src.agents.worker.GatewayWorker.chat", no_model)
    assert client.get("/health").json() == {"status": "ok", "mode": "demo"}
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "mode": "demo", "version": "0.3.0"}
    assert app.version == "0.3.0"


@pytest.mark.parametrize("kind", ["missing", "empty", "corrupt", "incomplete"])
def test_ready_rejects_unusable_database_without_creating_or_seeding_it(
    client, tmp_path, monkeypatch, kind
):
    """A probe never repairs, seeds or discloses a failing database."""
    path = tmp_path / "private-path" / "probe.db"
    if kind != "missing":
        path.parent.mkdir()
        if kind == "corrupt":
            path.write_bytes(b"not a SQLite database")
        else:
            path.touch()
            if kind == "incomplete":
                with sqlite3.connect(path) as connection:
                    connection.execute("CREATE TABLE users(id INTEGER PRIMARY KEY)")
    before = path.read_bytes() if path.exists() else None
    monkeypatch.setattr(db, "DB", path)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "error": "Database unavailable"}
    assert str(path) not in response.text
    if before is None:
        assert not path.parent.exists()
    else:
        assert path.read_bytes() == before
    assert client.get("/health").status_code == 200


def test_ready_rejects_missing_learning_table(client):
    """An authentication table alone does not establish learning readiness."""
    with db.connect() as connection:
        connection.execute("DROP TABLE learning_refreshes")
    assert client.get("/ready").status_code == 503


def test_ready_lock_wait_is_bounded_and_recovers(client):
    """A transient exclusive lock returns promptly and a later probe recovers."""
    connection = sqlite3.connect(db.DB)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        assert client.get("/ready").status_code == 503
        assert time.monotonic() - started < 3
    finally:
        connection.rollback()
        connection.close()
    assert client.get("/ready").status_code == 200


def test_ready_ignores_rehearsal_cookie_and_database_override(client, tmp_path):
    """Deployment probes cannot be redirected by a participant's workspace."""
    client.cookies.set("rehearsal", "0" * 32)
    scope = db.DATABASE_OVERRIDE.set(tmp_path / "absent-rehearsal.db")
    try:
        assert client.get("/ready").status_code == 200
    finally:
        db.DATABASE_OVERRIDE.reset(scope)

