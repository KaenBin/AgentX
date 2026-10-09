"""Measure disposable offline HTTP journeys; never target an existing deployment."""

import argparse
import asyncio
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import json
from importlib.metadata import version
import math
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

import httpx
import psutil

ROOT = Path(__file__).resolve().parent
PASSWORD = "LearnDemo2026!"


class BenchmarkFailure(Exception):
    """A sanitized HTTP or evidence failure; never include response contents."""


def require(condition, message):
    """Keep correctness checks active even when Python assertions are disabled."""
    if not condition:
        raise BenchmarkFailure(message)


def percentile(values, fraction):
    """Return a nearest-rank percentile, with zero for an empty request group."""
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * fraction) - 1)], 3) if ordered else 0


class RequestSamples:
    """Collect timings and statuses without retaining URLs, cookies or payloads."""

    def __init__(self):
        """Create per-operation samples owned by one asyncio event loop."""
        self.rows = defaultdict(list)

    async def request(self, client, operation, method, path, *, expected=200, **kwargs):
        """Time one request and reject unexpected statuses without exposing its body."""
        start = time.perf_counter()
        status = "transport_error"
        failed = True
        try:
            response = await client.request(method, path, **kwargs)
            status = str(response.status_code)
            require(response.status_code == expected, f"{operation}: unexpected HTTP status {status}")
            try:
                result = response.json() if expected == 200 else None
            except ValueError:
                raise BenchmarkFailure(f"{operation}: invalid JSON") from None
            failed = False
            return result
        except httpx.HTTPError:
            raise BenchmarkFailure(f"{operation}: transport failure") from None
        except asyncio.CancelledError:
            status, failed = "cancelled", False
            raise
        finally:
            self.rows[operation].append(((time.perf_counter() - start) * 1000,
                                         status, failed))

    def summary(self):
        """Summarize observed HTTP latency and errors, including expected denials."""
        groups = {}
        all_rows = []
        cancelled = 0
        for operation, rows in sorted(self.rows.items()):
            cancellations = sum(row[1] == "cancelled" for row in rows)
            cancelled += cancellations
            rows = [row for row in rows if row[1] != "cancelled"]
            all_rows.extend(rows)
            timings = [row[0] for row in rows]
            groups[operation] = {
                "count": len(rows), "cancelled": cancellations, "failed": sum(row[2] for row in rows),
                "statuses": dict(Counter(row[1] for row in rows)),
                "p50_ms": percentile(timings, .50), "p95_ms": percentile(timings, .95),
                "max_ms": round(max(timings), 3) if timings else 0,
            }
        failed = sum(row[2] for row in all_rows)
        timings = [row[0] for row in all_rows]
        return {"count": len(all_rows), "cancelled": cancelled, "failed": failed,
                "error_rate": failed / len(all_rows) if all_rows else 0,
                "p50_ms": percentile(timings, .50), "p95_ms": percentile(timings, .95),
                "by_operation": groups}


class ResourceSampler:
    """Sample the owned server process tree, including Windows venv redirectors."""

    def __init__(self, pid):
        """Monitor only the explicitly single-worker Uvicorn child."""
        self.process = psutil.Process(pid)
        self.rss = []
        self.max_processes = 0
        self.owned = {}
        self.stop = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self):
        """Capture resident memory, recording sampling failures as failed evidence."""
        while not self.stop.is_set():
            try:
                processes = self.process.children(recursive=True) + [self.process]
                self.owned.update({p.pid: p for p in processes})
                self.max_processes = max(self.max_processes, len(processes))
                self.rss.append(sum(p.memory_info().rss for p in processes))
            except psutil.Error:
                self.error = "Server resource sampling failed"
                return
            self.stop.wait(.1)

    def cpu_seconds(self):
        """Sum server-tree user/system CPU seconds, excluding the load driver."""
        total = 0
        for process in self.process.children(recursive=True) + [self.process]:
            times = process.cpu_times()
            total += times.user + times.system
        return total


def stop_server(process, known=()):
    """Stop only the owned child tree, even if a Windows launcher exits first."""
    owned = {p.pid: p for p in known}
    try:
        parent = psutil.Process(process.pid)
        owned.update({p.pid: p for p in parent.children(recursive=True)})
        owned[parent.pid] = parent
    except psutil.NoSuchProcess:
        pass
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    for child in owned.values():
        try:
            if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(list(owned.values()), timeout=3)
    for child in alive:
        if child.status() != psutil.STATUS_ZOMBIE:
            child.kill()
    _, alive = psutil.wait_procs(alive, timeout=3)
    require(all(p.status() == psutil.STATUS_ZOMBIE for p in alive), "Owned server did not stop")


def seed_clients(database, learners):
    """Add synthetic accounts only to the fresh benchmark database and read its bank."""
    with closing(sqlite3.connect(database)) as connection, connection:
        for index in range(learners):
            connection.execute(
                "INSERT INTO users(name,role,salt,password) SELECT ?,role,salt,password "
                "FROM users WHERE name='learner'", (f"benchmark-{index}",),
            )
        for course_id, content in connection.execute("SELECT id,content FROM courses ORDER BY id"):
            spec = json.loads(content).get("readiness")
            if spec:
                answers = {q["id"]: q["answer"] for obj in spec["objectives"]
                           for q in [obj["diagnostic"], *obj["reassessments"]]}
                return course_id, answers
    raise BenchmarkFailure("Fictional readiness bank missing")


async def workload(url, learners, rounds, course_id, answers, samples):
    """Run distinct learner journeys alongside a trainer, then verify API isolation."""
    clients = [httpx.AsyncClient(base_url=url, timeout=20, trust_env=False)
               for _ in range(learners + 1)]
    evidence = []

    async def journey(index, client):
        """Complete a diagnosis, deliberate first miss, remediation and fresh cases."""
        await samples.request(client, "login", "POST", "/api/login",
                              json={"name": f"benchmark-{index}", "password": PASSWORD})
        for _ in range(rounds):
            await samples.request(client, "state", "GET", "/api/state")
        session = await samples.request(client, "start", "POST", "/api/learning/start",
                                        json={"course_id": course_id})
        sid = session["id"]
        expected = {}
        missed = False
        for _ in range(32):
            if session["state"] == "ready":
                break
            session = (await samples.request(client, "next", "POST", f"/api/learning/{sid}/next"))["session"]
            activity = session["activity"]
            require(activity is not None, "Journey stopped before readiness")
            answer = None if activity["kind"] == "lesson" else answers[activity["activity_id"]]
            correct = None if answer is None else True
            if not missed and answer is not None:
                answer = (answer + 1) % len(activity["options"])
                correct = False
                missed = True
            result = await samples.request(client, "answer", "POST", f"/api/learning/{sid}/answer",
                                           json={"issued_id": activity["id"], "answer": answer})
            require(result["correct"] == correct, "Unexpected deterministic score")
            expected[activity["id"]] = (answer, correct)
            session = result["session"]
            resumed = await samples.request(client, "progress", "GET", f"/api/learning/{sid}")
            require(resumed == session, "Saved progress differs from submitted result")
        require(session["state"] == "ready" and missed, "Readiness journey incomplete")
        require(all(o["demonstrated"] for o in session["objectives"] if o["critical"]),
                "Critical objective not demonstrated")
        for _ in range(rounds):
            state = await samples.request(client, "state", "GET", "/api/state")
            require([s["id"] for s in state["learning_sessions"]] == [sid], "Learner state isolation failed")
        return {"sid": sid, "uid": state["user"]["id"], "answers": expected}

    async def trainer(client):
        """Read the trainer dashboard concurrently, and verify the final session set."""
        await samples.request(client, "trainer_login", "POST", "/api/login",
                              json={"name": "trainer", "password": PASSWORD})
        for _ in range(rounds):
            await samples.request(client, "trainer_state", "GET", "/api/state")

    try:
        tasks = [asyncio.create_task(journey(i, clients[i])) for i in range(learners)]
        tasks.append(asyncio.create_task(trainer(clients[-1])))
        try:
            results = await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        evidence = results[:-1]
        state = await samples.request(clients[-1], "trainer_state", "GET", "/api/state")
        require({s["id"] for s in state["learning_sessions"]} == {e["sid"] for e in evidence},
                "Trainer session set differs from saved journeys")
        if learners > 1:
            for index, client in enumerate(clients[:-1]):
                other = evidence[(index + 1) % learners]["sid"]
                await samples.request(client, "isolation_denial", "GET", f"/api/learning/{other}", expected=403)
        for client in clients:
            await samples.request(client, "logout", "POST", "/api/logout", json={})
        return evidence
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))


def verify_saved(database, evidence):
    """Compare persisted owners, answers and scores after the server has stopped."""
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        require(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Database integrity failed")
        require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "Database relationships failed")
        for learner in evidence:
            row = connection.execute("SELECT user_id FROM learning_sessions WHERE id=?", (learner["sid"],)).fetchone()
            require(row == (learner["uid"],), "Saved session owner differs")
            rows = connection.execute("SELECT id,answer,correct,submitted FROM learning_activities WHERE session_id=?",
                                      (learner["sid"],)).fetchall()
            actual = {row[0]: (row[1], None if row[2] is None else bool(row[2])) for row in rows if row[3] is not None}
            require(len(rows) == len(actual) and actual == learner["answers"], "Saved answers or scores differ")


def run_stage(*, learners, read_rounds, temp_root=None):
    """Own a temporary database and localhost server for one bounded workload."""
    if not 1 <= learners <= 100 or not 1 <= read_rounds <= 1000:
        raise ValueError("Use 1–100 learners and 1–1000 read rounds")
    with tempfile.TemporaryDirectory(prefix="agentx-benchmark-", dir=temp_root) as temporary:
        database = Path(temporary) / "training.db"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if not k.startswith("UVICORN_")}
        env.update(AGENT_MODE="demo", TRAINING_DB=str(database), LLM_GATEWAY_URL="",
                   LLM_GATEWAY_API_KEY="", LLM_MODEL="", PYTHONDONTWRITEBYTECODE="1")
        started = time.perf_counter()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--workers", "1", "--no-access-log"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        sampler = None
        samples = RequestSamples()
        try:
            sampler = ResourceSampler(process.pid)
            sampler.thread.start()
            url = f"http://127.0.0.1:{port}"
            with httpx.Client(base_url=url, timeout=1, trust_env=False) as client:
                deadline = time.perf_counter() + 30
                while time.perf_counter() < deadline and process.poll() is None:
                    try:
                        response = client.get("/ready")
                        if response.status_code == 200 and response.json().get("mode") == "demo":
                            break
                    except (httpx.HTTPError, ValueError):
                        pass
                    time.sleep(.05)
                else:
                    raise BenchmarkFailure("Owned demo server did not become ready")
            startup_ms = (time.perf_counter() - started) * 1000
            course_id, answers = seed_clients(database, learners)
            before_bytes = database.stat().st_size
            before_cpu = sampler.cpu_seconds()
            start = time.perf_counter()
            evidence = asyncio.run(workload(url, learners, read_rounds, course_id, answers, samples))
            elapsed = time.perf_counter() - start
            cpu_seconds = sampler.cpu_seconds() - before_cpu
            require(sampler.error is None and bool(sampler.rss), "Resource samples unavailable")
        except BenchmarkFailure as exc:
            exc.stage = {"learners": learners, "outcome": "failed", "requests": samples.summary()}
            raise
        finally:
            if sampler:
                sampler.stop.set()
                sampler.thread.join(timeout=2)
            stop_server(process, sampler.owned.values() if sampler else ())
        verify_saved(database, evidence)
        after_bytes = database.stat().st_size
        return {
            "outcome": "passed", "learners": learners, "trainer_clients": 1, "read_rounds": read_rounds,
            "startup_ms": round(startup_ms, 3), "workload_seconds": round(elapsed, 3),
            "requests": samples.summary(),
            "resources": {"sampling_interval_ms": 100, "sample_count": len(sampler.rss),
                          "peak_sampled_rss_bytes": max(sampler.rss),
                          "max_server_processes": sampler.max_processes,
                          "cpu_seconds": round(cpu_seconds, 6),
                          "average_cpu_cores": round(cpu_seconds / elapsed, 6)},
            "database": {"before_bytes": before_bytes, "after_bytes": after_bytes,
                         "growth_bytes": after_bytes - before_bytes},
            "correctness": {"learners_ready": learners, "saved_answers_verified": True,
                            "user_isolation_verified": True, "database_integrity_verified": True},
        }


def source_identity():
    """Require committed tracked files and benchmark inputs before recording a run."""
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    dirty = subprocess.check_output([*git, "status", "--porcelain", "--untracked-files=no"], text=True)
    require(not dirty.strip(), "Commit tracked changes before recording benchmark evidence")
    tracked = set(subprocess.check_output([*git, "ls-files", "-z"]).decode().split("\0"))
    inputs = [ROOT / "benchmark_demo.py", ROOT / "requirements.txt"]
    for folder in ("src", "agents/system_prompts"):
        inputs.extend(p for p in (ROOT / folder).rglob("*") if p.is_file()
                      and "__pycache__" not in p.parts and p.suffix != ".pyc")
    require(all(not p.is_symlink() and p.relative_to(ROOT).as_posix() in tracked for p in inputs),
            "Uncommitted benchmark inputs cannot identify a measured revision")
    return subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()


def main():
    """Write a new aggregate-only JSON report; refuse to overwrite an existing file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learners", type=int, nargs="+", default=[1, 5, 10])
    parser.add_argument("--read-rounds", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not all(1 <= n <= 100 for n in args.learners) or not 1 <= args.read_rounds <= 1000:
        parser.error("Use 1–100 learners and 1–1000 read rounds")
    report = {"format_version": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
              "outcome": "failed", "mode": "demo", "workers": 1, "stages": []}
    try:
        revision = source_identity()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve before startup, so a mistake cannot overwrite earlier evidence.
        with args.output.open("x", encoding="utf-8") as output:
            report.update(source_commit=revision, host={"os": platform.system(),
                "os_release": platform.release(), "architecture": platform.machine(),
                "python": platform.python_version(), "logical_cpus": psutil.cpu_count(),
                "total_memory_bytes": psutil.virtual_memory().total},
                dependencies={name: version(name)
                              for name in ("psutil", "httpx", "fastapi", "uvicorn")})
            try:
                for learners in args.learners:
                    try:
                        report["stages"].append(run_stage(learners=learners, read_rounds=args.read_rounds))
                    except (BenchmarkFailure, OSError, ValueError, psutil.Error) as exc:
                        report["stages"].append(getattr(exc, "stage", {
                            "learners": learners, "outcome": "failed", "failure_kind": type(exc).__name__,
                        }))
                        raise
                report["outcome"] = "passed"
            finally:
                json.dump(report, output, indent=2)
                output.write("\n")
    except (BenchmarkFailure, OSError, ValueError, psutil.Error, subprocess.SubprocessError):
        print("Benchmark failed. Check committed inputs, a new output path and the local environment.", file=sys.stderr)
        return 1
    print(f"Benchmark passed: {len(report['stages'])} stages; report saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
