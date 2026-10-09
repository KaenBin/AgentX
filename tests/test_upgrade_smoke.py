"""Ensure the upgrade evidence checks detect damage rather than count rows alone."""

from copy import deepcopy
import sqlite3
import subprocess

import pytest

from upgrade_smoke import assert_preserved, snapshot_backup
import upgrade_smoke


@pytest.fixture
def backup(tmp_path):
    """Make real SQLite records with stable references and a companion rehearsal."""
    with sqlite3.connect(tmp_path / "training.db") as connection:
        connection.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE learning_sessions(id INTEGER PRIMARY KEY, course_id INTEGER REFERENCES courses(id));
            CREATE TABLE learning_activities(id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES learning_sessions(id), correct INTEGER);
            CREATE TABLE sessions(token TEXT PRIMARY KEY);
            INSERT INTO courses VALUES(7, 'Fictional procedure');
            INSERT INTO learning_sessions VALUES(10, 7);
            INSERT INTO learning_activities VALUES(21, 10, 1);
            INSERT INTO sessions VALUES('private-cookie');
        """)
    rehearsal = tmp_path / "rehearsals" / "fixture.db"
    rehearsal.parent.mkdir()
    rehearsal.write_bytes(b"fictional rehearsal")
    return tmp_path


def test_snapshot_records_values_and_companion_hash_without_auth_tokens(backup):
    """Evidence compares values and links while excluding rotating login cookies."""
    result = snapshot_backup(backup)
    assert result["tables"]["learning_activities"]["rows"] == [[21, 10, 1]]
    assert result["tables"]["learning_sessions"]["rows"] == [[10, 7]]
    assert "sessions" not in result["tables"]
    assert len(result["files"]["rehearsals/fixture.db"]) == 64
    assert_preserved(result, snapshot_backup(backup))


@pytest.mark.parametrize("damage", ["score", "relationship", "removed", "added", "columns", "companion"])
def test_preservation_detects_changed_evidence_without_disclosing_rows(backup, damage):
    """Same row counts cannot hide altered scores, relationships or backup files."""
    expected = snapshot_backup(backup)
    actual = deepcopy(expected)
    if damage == "score":
        actual["tables"]["learning_activities"]["rows"][0][2] = 0
    elif damage == "relationship":
        actual["tables"]["learning_sessions"]["rows"][0][1] = 99
    elif damage == "removed":
        del actual["tables"]["learning_activities"]
    elif damage == "added":
        actual["tables"]["unexpected"] = {"rows": [], "columns": []}
    elif damage == "columns":
        actual["tables"]["learning_activities"]["columns"].reverse()
    else:
        actual["files"]["rehearsals/fixture.db"] = "altered"
    with pytest.raises(AssertionError) as error:
        assert_preserved(expected, actual)
    assert "Fictional procedure" not in str(error.value)
    assert "private-cookie" not in str(error.value)


def test_snapshot_rejects_broken_relationships(backup):
    """A copied database must retain valid relationships before use as evidence."""
    with sqlite3.connect(backup / "training.db") as connection:
        connection.execute("UPDATE learning_sessions SET course_id=99")
    with pytest.raises(AssertionError, match="relationships"):
        snapshot_backup(backup)


def test_snapshot_never_creates_missing_database(tmp_path):
    """An empty backup is a failure rather than an apparently valid blank database."""
    with pytest.raises(sqlite3.OperationalError):
        snapshot_backup(tmp_path)
    assert not (tmp_path / "training.db").exists()


@pytest.fixture
def source(tmp_path):
    """Create a committed build context, without relying on the working checkout."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text('print("fictional")')
    (tmp_path / "Dockerfile").write_text("COPY src/ ./src/\n")
    (tmp_path / ".dockerignore").write_text("**/__pycache__/\n**/*.pyc\n")
    (tmp_path / "requirements-runtime.txt").write_text("")
    (tmp_path / ".gitignore").write_text("*.log\n__pycache__/\n")
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture"],
                   check=True, capture_output=True)
    return tmp_path


@pytest.mark.parametrize("name", ["src/untracked.py", "src/ignored.log"])
def test_source_identity_rejects_uncommitted_build_inputs(source, name):
    """An ignored or untracked file copied into an image breaks commit identity."""
    (source / name).write_text("uncommitted build material")
    with pytest.raises(AssertionError, match="build inputs"):
        upgrade_smoke.assert_clean_source(source)


def test_source_identity_allows_unrelated_files_and_docker_excluded_cache(source):
    """Local tools and excluded Python bytecode do not contaminate a clean image."""
    (source / "notes.txt").write_text("unrelated working file")
    cache = source / "src/__pycache__"
    cache.mkdir()
    (cache / "app.pyc").write_bytes(b"ignored bytecode")
    (source / "src/app.pyc").write_bytes(b"also excluded")
    assert len(upgrade_smoke.assert_clean_source(source)) == 40


def test_source_identity_rejects_changed_tracked_source(source):
    """An existing path must also match the committed revision's contents."""
    (source / "src/app.py").write_text("changed build material")
    with pytest.raises(AssertionError, match="tracked changes"):
        upgrade_smoke.assert_clean_source(source)
