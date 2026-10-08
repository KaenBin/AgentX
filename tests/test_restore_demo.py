"""Restore preconditions must preserve data when the application is active."""

import json
import io
import subprocess
import tarfile

import pytest

from restore_demo import restore_backup
from src.tools.restore_files import extract_backup


@pytest.mark.parametrize("state", ["running", "paused", "restarting", "removing", "unknown"])
def test_restore_rejects_active_or_unknown_app_state(monkeypatch, tmp_path, state):
    """Reject all unsafe states before an extraction container can run."""
    (tmp_path / "training.db").write_bytes(b"backup")
    calls = []

    def docker(command, **kwargs):
        calls.append(command)
        if "ps" in command:
            # Compose's running-only query omits paused/restarting containers.
            output = (json.dumps({"State": state}) if "--format" in command
                      else "container-id" if state == "running" else "")
        else:
            output = ""
        return subprocess.CompletedProcess(command, 0, stdout=output)

    monkeypatch.setattr(subprocess, "run", docker)
    with pytest.raises(ValueError, match="Stop"):
        restore_backup(tmp_path, project="restore-test")
    assert len(calls) == 1, "Unsafe state must not launch extraction"


def backup_stream():
    """Build a small snapshot to exercise real filesystem extraction."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        member = tarfile.TarInfo("training.db")
        member.size = 8
        archive.addfile(member, io.BytesIO(b"snapshot"))
    stream.seek(0)
    return stream


def test_restore_refuses_nonempty_destination_without_writing(tmp_path):
    """Retain existing files and refuse to mix snapshots with stale data."""
    stale = tmp_path / "training.db-wal"
    stale.write_bytes(b"existing journal")
    with pytest.raises(ValueError, match="empty"):
        extract_backup(backup_stream(), tmp_path)
    assert stale.read_bytes() == b"existing journal"
    assert not (tmp_path / "training.db").exists()


def test_restore_extracts_into_empty_destination(tmp_path):
    """Restore the backup without introducing files absent from its snapshot."""
    extract_backup(backup_stream(), tmp_path)
    assert (tmp_path / "training.db").read_bytes() == b"snapshot"
    assert {path.name for path in tmp_path.iterdir()} == {"training.db"}
