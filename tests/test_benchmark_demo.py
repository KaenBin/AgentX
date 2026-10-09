"""Check benchmark evidence against real HTTP writes in disposable storage."""

import json

import pytest


def test_concurrent_readiness_journeys_preserve_results_and_leave_existing_data(tmp_path, monkeypatch):
    """Independent learners complete remediation without touching the user's data."""
    import benchmark_demo

    sentinel = tmp_path / "existing.db"
    sentinel.write_bytes(b"existing demo must survive")
    monkeypatch.setenv("TRAINING_DB", str(sentinel))
    monkeypatch.setenv("AGENT_MODE", "gateway")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "private-inherited-credential")
    report = benchmark_demo.run_stage(learners=3, read_rounds=2, temp_root=tmp_path)
    assert report["correctness"] == {
        "learners_ready": 3, "saved_answers_verified": True,
        "user_isolation_verified": True, "database_integrity_verified": True,
    }
    assert report["requests"]["failed"] == 0
    assert report["requests"]["count"] > 30
    assert report["resources"]["peak_sampled_rss_bytes"] > 0
    assert report["resources"]["cpu_seconds"] >= 0
    assert report["startup_ms"] > 0
    assert report["database"]["growth_bytes"] > 0
    assert report["learners"] == 3
    assert report["trainer_clients"] == 1
    assert report["requests"]["by_operation"]["answer"]["count"] >= 3
    rendered = json.dumps(report)
    assert "LearnDemo2026!" not in rendered
    assert "private-inherited-credential" not in rendered
    assert "session=" not in rendered
    assert "benchmark-" not in rendered
    assert str(tmp_path) not in rendered
    assert sentinel.read_bytes() == b"existing demo must survive"
    assert list(tmp_path.iterdir()) == [sentinel]


@pytest.mark.parametrize("learners,rounds", [(0, 1), (101, 1), (1, 0), (1, 1001)])
def test_invalid_workloads_fail_before_creating_files(tmp_path, learners, rounds):
    """Bound workload size and reject empty benchmarks before startup."""
    import benchmark_demo

    with pytest.raises(ValueError):
        benchmark_demo.run_stage(learners=learners, read_rounds=rounds, temp_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_request_failures_are_counted_without_copying_response_content():
    """A failing endpoint cannot be described as a passing performance sample."""
    import asyncio
    import httpx
    import benchmark_demo

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(503, text="secret payload")
        ), base_url="http://fixture.invalid") as client:
            samples = benchmark_demo.RequestSamples()
            with pytest.raises(benchmark_demo.BenchmarkFailure) as error:
                await samples.request(client, "state", "GET", "/api/state")
            assert "secret" not in str(error.value)
            result = samples.summary()
            assert result["failed"] == 1
            assert result["count"] == 1
            assert result["by_operation"]["state"]["statuses"] == {"503": 1}

    asyncio.run(exercise())


def test_invalid_json_is_counted_as_a_failed_response():
    """HTTP 200 with an unusable body must not count as a successful sample."""
    import asyncio
    import httpx
    import benchmark_demo

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="private invalid body")
        ), base_url="http://fixture.invalid") as client:
            samples = benchmark_demo.RequestSamples()
            with pytest.raises(benchmark_demo.BenchmarkFailure, match="invalid JSON"):
                await samples.request(client, "state", "GET", "/api/state")
            assert samples.summary()["failed"] == 1
            assert "private" not in json.dumps(samples.summary())

    asyncio.run(exercise())


def test_failed_journey_stops_server_and_removes_temporary_database(tmp_path, monkeypatch):
    """Cleanup applies after workload failure as well as a successful stage."""
    import benchmark_demo

    async def fail(*args):
        raise benchmark_demo.BenchmarkFailure("Scripted fixture failure")

    monkeypatch.setattr(benchmark_demo, "workload", fail)
    with pytest.raises(benchmark_demo.BenchmarkFailure):
        benchmark_demo.run_stage(learners=1, read_rounds=1, temp_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("damage", ["owner", "answer", "score", "pending", "removed"])
def test_persisted_evidence_verifier_detects_mutation(tmp_path, damage):
    """Equal row counts cannot hide changed ownership, answers or deterministic scores."""
    import sqlite3
    import benchmark_demo

    database = tmp_path / "fixture.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE learning_sessions(id INTEGER PRIMARY KEY,user_id INTEGER);
            CREATE TABLE learning_activities(id INTEGER PRIMARY KEY,session_id INTEGER,answer INTEGER,correct INTEGER,submitted REAL);
            INSERT INTO learning_sessions VALUES(1,7);
            INSERT INTO learning_activities VALUES(2,1,0,1,123);
        """)
        statement = {
            "owner": "UPDATE learning_sessions SET user_id=8",
            "answer": "UPDATE learning_activities SET answer=1",
            "score": "UPDATE learning_activities SET correct=0",
            "pending": "UPDATE learning_activities SET submitted=NULL",
            "removed": "DELETE FROM learning_activities",
        }[damage]
        connection.execute(statement)
    with pytest.raises(benchmark_demo.BenchmarkFailure):
        benchmark_demo.verify_saved(database, [{"sid": 1, "uid": 7, "answers": {2: (0, True)}}])


def test_cli_preserves_previous_report_and_records_failed_stage(tmp_path, monkeypatch):
    """Failed evidence remains explicit and a rerun cannot overwrite prior evidence."""
    import sys
    import benchmark_demo

    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["benchmark_demo.py", "--learners", "1", "--output", str(output)])
    monkeypatch.setattr(benchmark_demo, "source_identity", lambda: "a" * 40)

    def fail(**kwargs):
        raise benchmark_demo.BenchmarkFailure("private exception detail")

    monkeypatch.setattr(benchmark_demo, "run_stage", fail)
    assert benchmark_demo.main() == 1
    report = json.loads(output.read_text())
    assert report["outcome"] == "failed"
    assert report["stages"] == [{"learners": 1, "outcome": "failed", "failure_kind": "BenchmarkFailure"}]
    assert "private exception" not in output.read_text()
    original = output.read_bytes()
    assert benchmark_demo.main() == 1
    assert output.read_bytes() == original


def test_cancelled_peer_requests_do_not_inflate_http_failure_count():
    """Coordinator cancellation is separate from an observed transport/HTTP failure."""
    import asyncio
    import httpx
    import benchmark_demo

    async def exercise():
        entered = asyncio.Event()

        async def wait(request):
            entered.set()
            await asyncio.Event().wait()

        async with httpx.AsyncClient(transport=httpx.MockTransport(wait), base_url="http://fixture.invalid") as client:
            samples = benchmark_demo.RequestSamples()
            task = asyncio.create_task(samples.request(client, "state", "GET", "/api/state"))
            await entered.wait()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            assert samples.summary()["failed"] == 0
            assert samples.summary()["cancelled"] == 1

    asyncio.run(exercise())


def test_resources_and_shutdown_include_owned_child_processes(tmp_path):
    """Windows venv redirectors and other owned descendants must be measured/stopped."""
    import subprocess
    import sys
    import time
    import psutil
    import benchmark_demo

    marker = tmp_path / "ready"
    child_code = "import time; from pathlib import Path; blob=bytearray(64*1024*1024); " + f"Path({str(marker)!r}).write_text('ready'); time.sleep(60)"
    parent_code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child_code!r}]); time.sleep(60)"
    process = subprocess.Popen([sys.executable, "-c", parent_code])
    sampler = benchmark_demo.ResourceSampler(process.pid)
    sampler.thread.start()
    descendants = []
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        assert marker.exists()
        descendants = psutil.Process(process.pid).children(recursive=True)
        time.sleep(.2)
        assert max(sampler.rss) >= 64 * 1024 * 1024
        assert sampler.max_processes >= 2
    finally:
        sampler.stop.set()
        sampler.thread.join(timeout=2)
        try:
            benchmark_demo.stop_server(process)
            assert all(not p.is_running() or p.status() == psutil.STATUS_ZOMBIE for p in descendants)
        finally:
            for child in descendants:
                if child.is_running():
                    child.kill()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)


def test_sampling_error_published_during_join_rejects_the_stage(tmp_path, monkeypatch):
    """A final sampler error cannot turn into apparently passing resource evidence."""
    import benchmark_demo

    def finish_with_error(sampler):
        """Publish the fault only after the coordinator asks sampling to stop."""
        sampler.rss.append(1)
        sampler.stop.wait(timeout=30)
        sampler.error = "Scripted final sampling failure"

    monkeypatch.setattr(benchmark_demo.ResourceSampler, "_sample", finish_with_error)
    with pytest.raises(benchmark_demo.BenchmarkFailure, match="Resource samples unavailable"):
        benchmark_demo.run_stage(learners=1, read_rounds=1, temp_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure_kind", ["sqlite", "timeout", "runtime"])
def test_cli_records_native_stage_failures_without_disclosing_exception_data(tmp_path, monkeypatch, capsys, failure_kind):
    """SQLite and shutdown failures must produce a failed stage and generic CLI error."""
    import sqlite3
    import subprocess
    import sys
    import benchmark_demo

    output = tmp_path / "failed.json"
    failure = {
        "sqlite": sqlite3.OperationalError("private database path"),
        "timeout": subprocess.TimeoutExpired("private command arguments", 10),
        "runtime": RuntimeError("private failure context"),
    }[failure_kind]
    monkeypatch.setattr(sys, "argv", ["benchmark_demo.py", "--learners", "1", "--output", str(output)])
    monkeypatch.setattr(benchmark_demo, "source_identity", lambda: "a" * 40)

    def fail(**kwargs):
        """Inject an ordinary exception at the CLI stage boundary."""
        raise failure

    monkeypatch.setattr(benchmark_demo, "run_stage", fail)
    assert benchmark_demo.main() == 1
    report = json.loads(output.read_text())
    assert report["outcome"] == "failed"
    assert report["stages"] == [{"learners": 1, "outcome": "failed", "failure_kind": type(failure).__name__}]
    captured = capsys.readouterr()
    assert "Benchmark failed." in captured.err
    assert "private" not in captured.err + captured.out + output.read_text()


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_cli_preserves_interruption_signals(tmp_path, monkeypatch, signal):
    """The ordinary-failure boundary must not swallow cancellation or explicit exit."""
    import sys
    import benchmark_demo

    output = tmp_path / "interrupted.json"
    monkeypatch.setattr(sys, "argv", ["benchmark_demo.py", "--learners", "1", "--output", str(output)])
    monkeypatch.setattr(benchmark_demo, "source_identity", lambda: "a" * 40)

    def interrupt(**kwargs):
        """Raise a BaseException that the CLI must allow through."""
        raise signal()

    monkeypatch.setattr(benchmark_demo, "run_stage", interrupt)
    with pytest.raises(signal):
        benchmark_demo.main()
    assert json.loads(output.read_text())["outcome"] == "failed"
