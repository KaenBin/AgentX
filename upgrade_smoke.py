"""Rehearse a pinned demo upgrade and matching-backup rollback in disposable volumes."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import urllib.request
import uuid

from restore_demo import restore_backup

PREVIOUS_REVISION = "8c5a357043fbfa5e562b49afc693894e5f3d435b"


def assert_clean_source(source):
    """Require committed Docker inputs while allowing unrelated local files."""
    git = ["git", "-C", str(source)]
    dirty = subprocess.check_output(
        [*git, "status", "--porcelain", "--untracked-files=no"], text=True,
    ).strip()
    assert not dirty, "Commit tracked changes before recording a revision-based rehearsal"
    tracked = set(subprocess.check_output(
        [*git, "ls-tree", "-r", "-z", "--name-only", "HEAD"],
    ).decode("utf-8").split("\0"))
    inputs = [source / name for name in ("Dockerfile", ".dockerignore", "requirements-runtime.txt")]
    for name in ("src", "agents/system_prompts"):
        inputs.extend(path for path in (source / name).rglob("*")
                      if (path.is_file() or path.is_symlink())
                      and "__pycache__" not in path.parts and path.suffix != ".pyc")
    assert all(not path.is_symlink() and path.relative_to(source).as_posix() in tracked
               for path in inputs), "Uncommitted or symbolic build inputs cannot identify a tested revision"
    return subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()


def snapshot_backup(directory):
    """Validate a stopped copy and capture rows plus hashes of companion files."""
    database = directory / "training.db"
    tables = {}
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Database integrity failed"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == [], "Broken database relationships"
        names = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        for name in names:
            # Authentication sessions can change on login; user and learning rows cannot.
            if name == "sessions":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            cursor = connection.execute(f"SELECT * FROM {quoted} ORDER BY rowid")
            tables[name] = {"columns": [column[0] for column in cursor.description],
                            "rows": [list(row) for row in cursor]}
    files = {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path != database
    }
    return {"tables": tables, "files": files}


def assert_preserved(expected, actual):
    """Fail on missing, altered or added evidence without printing private rows."""
    assert actual["tables"].keys() == expected["tables"].keys(), "Database table set changed"
    for name, contents in expected["tables"].items():
        assert actual["tables"][name] == contents, f"Saved rows or columns changed: {name}"
    assert actual["files"] == expected["files"], "Rehearsal or companion files changed"


class Demo:
    """Operate only a unique rehearsal project using a selected local image."""

    def __init__(self, root, directory, image, suffix):
        """Allocate an unused localhost port and an explicit Compose image override."""
        self.root = root
        self.project = "agentx-upgrade-" + suffix
        self.override = directory / (suffix + ".json")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        # Compose interpolation reads this file rather than the user's .env or port.
        self.environment = directory / (suffix + ".env")
        self.environment.write_text(f"DEMO_PORT={self.port}\n", encoding="utf-8")
        self.files = (root / "compose.yaml", self.override)
        self.select_image(image)
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def select_image(self, image):
        """Select an already-built image without retagging a normal demo image."""
        self.override.write_text(json.dumps({"services": {"app": {"image": image}}}), encoding="utf-8")

    def compose(self, *args):
        """Run bounded Compose operations scoped to this project's configuration."""
        command = ["docker", "compose", "--env-file", str(self.environment)]
        for path in self.files:
            command += ["-f", str(path)]
        return subprocess.run(
            [*command, "-p", self.project, *args], cwd=self.root, check=True,
            env=os.environ | {"DEMO_PORT": str(self.port)},
            capture_output=True, text=True, timeout=240,
        ).stdout.strip()

    def start(self, version):
        """Start without building or pulling and verify the running API version."""
        self.compose("up", "-d", "--no-build", "--pull", "never", "--wait", "--wait-timeout", "90")
        assert self.request("/openapi.json")["info"]["version"] == version, "Unexpected app version"

    def request(self, path, payload=None):
        """Use the real HTTP API with this fictional participant's session cookies."""
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=data,
            headers={"Content-Type": "application/json"} if data is not None else {},
        )
        with self.opener.open(request, timeout=15) as response:
            return json.load(response)

    def login(self, name):
        """Sign in as one of the seeded fictional demo accounts."""
        assert self.request("/api/login", {"name": name, "password": "LearnDemo2026!"})["ok"]

    def backup(self, path):
        """Stop the app before copying its complete volume and validating the copy."""
        self.compose("stop", "app")
        self.compose("cp", "app:/app/data", str(path))
        return snapshot_backup(path)

    def restore(self, path):
        """Use the supported helper with exactly this rehearsal's image and project."""
        self.compose("create", "--no-build", "app")
        restore_backup(path, project=self.project, compose_files=self.files)


def answer_for(course, activity):
    """Read the trainer's fictional answer bank solely for automated fixture scoring."""
    if activity["kind"] == "lesson":
        return None
    objective = next(item for item in course["content"]["readiness"]["objectives"]
                     if item["id"] == activity["objective_id"])
    return next(item["answer"] for item in [objective["diagnostic"], *objective["reassessments"]]
                if item["id"] == activity["activity_id"])


def populate(demo):
    """Save completed and in-flight learning, decisions and a separate rehearsal."""
    demo.login("trainer")
    course = next(item for item in demo.request("/api/state")["courses"]
                  if "readiness" in item["content"])
    assert demo.request("/api/rehearsal/start", {"mode": "demo"})["ok"]
    assert demo.request("/api/rehearsal/exit", {})["ok"]
    demo.login("learner")
    completed = demo.request("/api/learning/start", {"course_id": course["id"]})
    for turn in range(60):
        if completed["state"] == "ready":
            break
        completed = demo.request(f"/api/learning/{completed['id']}/next", {})["session"]
        activity = completed["activity"]
        answer = answer_for(course, activity)
        if turn == 0:
            answer = (answer + 1) % len(activity["options"])
        completed = demo.request(f"/api/learning/{completed['id']}/answer",
                                 {"issued_id": activity["id"], "answer": answer})["session"]
    assert completed["state"] == "ready" and completed["score"] == 100
    assert completed["decisions"] and all(item["demonstrated"] for item in completed["objectives"])
    demo.login("alex")
    pending = demo.request("/api/learning/start", {"course_id": course["id"]})
    pending = demo.request(f"/api/learning/{pending['id']}/next", {})["session"]
    assert pending["activity"] and pending["activity"]["id"]
    return course, completed, pending


def run(previous_source, report):
    """Build both reviewed sources and prove upgrade, recovery and snapshot rollback."""
    root = Path(__file__).resolve().parent
    previous_source = previous_source.resolve(strict=True)
    assert previous_source != root, "Previous source must be a separate clean checkout"
    previous_revision = assert_clean_source(previous_source)
    assert previous_revision == PREVIOUS_REVISION, "Previous checkout must match the pinned baseline"
    current_revision = assert_clean_source(root)
    # The current release version is read without importing FastAPI on the host.
    from src.core.version import VERSION

    suffix = uuid.uuid4().hex[:12]
    images = ["agentx-upgrade:" + suffix + "-previous", "agentx-upgrade:" + suffix + "-current"]
    with tempfile.TemporaryDirectory(prefix="agentx-upgrade-") as temporary:
        directory = Path(temporary)
        demo = Demo(root, directory, images[0], suffix)
        rollback = Demo(root, directory, images[1], suffix + "-rollback")
        try:
            for source, image in zip((previous_source, root), images):
                subprocess.run(["docker", "build", "-t", image, str(source)], check=True, timeout=600)
            image_ids = [subprocess.check_output(
                ["docker", "image", "inspect", "--format", "{{.Id}}", image], text=True,
            ).strip() for image in images]
            demo.start("0.2.0")
            course, completed, pending = populate(demo)
            baseline = demo.backup(directory / "before")
            assert baseline["files"], "The backup must contain rehearsal files"
            demo.select_image(images[1])
            demo.start(VERSION)
            assert demo.request("/ready")["status"] == "ready"
            assert demo.request(f"/api/learning/{pending['id']}") == pending, "Pending evidence changed on upgrade"
            demo.login("learner")
            assert demo.request(f"/api/learning/{completed['id']}") == completed, "Completed evidence changed on upgrade"
            assert_preserved(baseline, demo.backup(directory / "after-upgrade"))
            demo.start(VERSION)
            demo.login("alex")
            updated = demo.request(f"/api/learning/{pending['id']}/answer", {
                "issued_id": pending["activity"]["id"], "answer": answer_for(course, pending["activity"]),
            })["session"]
            assert updated != pending and updated["decisions"][0]["submitted"] is not None
            recovery = demo.backup(directory / "after-write")
            demo.compose("down", "--volumes", "--remove-orphans")
            demo.restore(directory / "after-write")
            demo.start(VERSION)
            assert demo.request(f"/api/learning/{pending['id']}") == updated, "New write lost during recovery"
            assert_preserved(recovery, demo.backup(directory / "recovered"))
            # Extract with the reviewed current helper, then start the old image.
            rollback.restore(directory / "before")
            rollback.select_image(images[0])
            rollback.start("0.2.0")
            rollback.login("alex")
            assert rollback.request(f"/api/learning/{pending['id']}") == pending, "Rollback did not restore old evidence"
            rollback.login("learner")
            assert rollback.request(f"/api/learning/{completed['id']}") == completed
            assert_preserved(baseline, rollback.backup(directory / "rolled-back"))
            result = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "previous_revision": previous_revision, "current_revision": current_revision,
                "previous_version": "0.2.0", "current_version": VERSION,
                "local_image_ids": image_ids,
                "checks": {"upgrade_preserved_evidence": True, "new_answer_saved": True,
                           "recovery_preserved_new_answer": True, "matching_backup_rollback": True},
                "table_row_counts": {name: len(value["rows"]) for name, value in baseline["tables"].items()},
                "baseline_sha256": hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest(),
                "companion_file_count": len(baseline["files"]),
            }
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print("Upgrade smoke passed: 0.2.0 -> " + VERSION + "; learning evidence, new writes, recovery and matching-backup rollback.")
        finally:
            cleanup_errors = []
            for instance in (demo, rollback):
                try:
                    instance.compose("down", "--volumes", "--remove-orphans")
                except subprocess.SubprocessError as error:
                    cleanup_errors.append(error)
            # A failed build may not have produced both tags; removal is best effort.
            subprocess.run(["docker", "image", "rm", *images], check=False, timeout=60)
            if cleanup_errors:
                raise RuntimeError("Rehearsal cleanup failed; inspect the agentx-upgrade projects") from cleanup_errors[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous_source", type=Path, help="Separate checkout of the pinned 0.2.0 revision")
    parser.add_argument("--report", type=Path, default=Path("output/upgrade/rehearsal.json"))
    arguments = parser.parse_args()
    run(arguments.previous_source, arguments.report)
