"""Exercise an isolated demo container; never touch the normal demo volume."""

import http.cookiejar
from contextlib import closing
import json
import os
import re
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import urllib.request
import uuid
from restore_demo import restore_backup


def main():
    """Check demo deployment and recovery in a disposable Compose project."""
    root = Path(__file__).resolve().parent
    project = "agentx-smoke-" + uuid.uuid4().hex[:12]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ | {"DEMO_PORT": str(port)}

    def compose(*args, capture=False):
        """Run Compose against this test's unique project and port."""
        result = subprocess.run(
            ["docker", "compose", "-p", project, *args],
            cwd=root, env=env, check=True, text=True,
            stdout=subprocess.PIPE if capture else None,
            timeout=180,
        )
        return result.stdout.strip() if capture else None

    def execute(code):
        """Execute a runtime assertion inside the unprivileged app container."""
        return compose("exec", "-T", "app", "python", "-c", code, capture=True)

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def request(path, payload=None):
        """Send an HTTP request while preserving the smoke user's cookies."""
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with opener.open(req, timeout=10) as response:
            assert re.fullmatch(r"[0-9a-f]{32}", response.headers.get("X-Request-ID", "")), "Response request ID missing"
            return response.read()

    try:
        compose("up", "--build", "-d", "--wait", "--wait-timeout", "90")
        assert json.loads(request("/health")) == {"status": "ok", "mode": "demo"}
        assert json.loads(request("/ready")) == {
            "status": "ready", "mode": "demo", "version": "0.3.0"
        }
        canary = "private-query-" + project
        request("/health?private=" + canary)
        logs = compose("logs", "--no-color", "app", capture=True)
        assert '"event": "http_request"' in logs, "Structured request diagnostics missing"
        assert canary not in logs, "Query text must not appear in container logs"
        assert b"AgentX" in request("/")
        assert json.loads(request("/api/login", {
            "name": "learner", "password": "LearnDemo2026!"
        }))["ok"]
        state = json.loads(request("/api/state"))
        assert state["courses"], "Seeded courses must be available"
        assert execute("import os; print(os.getuid())") == "10001"
        execute("from pathlib import Path; assert not Path('/app/.env').exists(); "
                "assert not Path('/app/tests').exists()")
        execute("import importlib.util; assert importlib.util.find_spec('pytest') is None")
        marker = "container persistence smoke " + project
        execute("import sqlite3; c=sqlite3.connect('/app/data/training.db'); "
                f"c.execute('INSERT INTO events(action,detail) VALUES(?,?)', ('smoke', {marker!r})); "
                "c.commit(); c.close()")
        with tempfile.TemporaryDirectory(prefix=project) as directory:
            backup = str(Path(directory) / "data")
            compose("stop", "app")
            compose("cp", "app:/app/data", backup)
            with closing(sqlite3.connect(str(Path(backup) / "training.db"))) as db:
                assert db.execute("SELECT detail FROM events WHERE action='smoke'").fetchone()[0] == marker
            compose("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "90")
            execute("import sqlite3; c=sqlite3.connect('/app/data/training.db'); "
                    f"assert c.execute('SELECT detail FROM events WHERE action=?', ('smoke',)).fetchone()[0] == {marker!r}")
            try:
                restore_backup(Path(backup), project=project)
            except ValueError as exc:
                assert "stop" in str(exc).lower()
            else:
                raise AssertionError("Restore must refuse a running application")
            compose("pause", "app")
            try:
                try:
                    restore_backup(Path(backup), project=project)
                except ValueError as exc:
                    assert "stop" in str(exc).lower()
                else:
                    raise AssertionError("Restore must refuse a paused application")
            finally:
                compose("unpause", "app")
            compose("stop", "app")
            compose("run", "--rm", "-T", "--no-deps", "app", "python", "-c",
                    "from pathlib import Path; Path('/app/data/training.db').unlink(); "
                    "Path('/app/data/stale-only.txt').write_text('preserve until operator removes')")
            try:
                restore_backup(Path(backup), project=project)
            except subprocess.CalledProcessError:
                pass
            else:
                raise AssertionError("Restore must refuse a non-empty data directory")
            compose("run", "--rm", "-T", "--no-deps", "app", "python", "-c",
                    "from pathlib import Path; "
                    "assert not Path('/app/data/training.db').exists(); "
                    "assert Path('/app/data/stale-only.txt').read_text() == 'preserve until operator removes'; "
                    "Path('/app/data/stale-only.txt').unlink()")
            restore_backup(Path(backup), project=project)
            compose("up", "-d", "--wait", "--wait-timeout", "90")
            execute("import sqlite3; c=sqlite3.connect('/app/data/training.db'); "
                    f"assert c.execute('SELECT detail FROM events WHERE action=?', ('smoke',)).fetchone()[0] == {marker!r}")
            execute("from pathlib import Path; assert not Path('/app/data/stale-only.txt').exists()")
        assert json.loads(request("/health"))["status"] == "ok"
        print("Container smoke passed: readiness, request IDs, safe logs, login, seeded content, non-root runtime, backup, restore, persistence.")
    except Exception:
        compose("logs", "--tail", "100")
        raise
    finally:
        # Only this script's unique disposable project is removed.
        compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
