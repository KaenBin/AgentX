"""Real browser checks against disposable offline application instances."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Expose failure results to browser teardown for diagnostic capture."""
    result = yield
    setattr(item, "rep_" + call.when, result.get_result())


@pytest.fixture
def demo_url(tmp_path):
    """Start a fresh demo database and stop its server after each case."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    env = os.environ | {
        "AGENT_MODE": "demo", "TRAINING_DB": str(tmp_path / "training.db"),
        "LLM_GATEWAY_URL": "", "LLM_GATEWAY_API_KEY": "", "LLM_MODEL": "",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    log_path = tmp_path / "server.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--no-access-log"], cwd=ROOT, env=env, stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1) as response:
                        assert json.load(response) == {"status": "ok", "mode": "demo"}
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                pytest.fail("Demo server did not start:\n" + log_path.read_text()[-3000:])
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


@pytest.fixture(scope="session")
def browser():
    """Share a Chromium process while isolating contexts and server data."""
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=True)
        yield instance
        instance.close()


@pytest.fixture
def page(browser, demo_url, request):
    """Capture screenshots and traces only for failed fictional-data cases."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    completed = False
    try:
        page.goto(demo_url, wait_until="networkidle")
        yield page
        assert not errors, "Uncaught browser errors: " + "; ".join(errors)
        completed = True
    finally:
        failed = getattr(request.node, "rep_call", None)
        if not completed or (failed and failed.failed) or errors:
            output = ROOT / "output" / "browser" / request.node.name
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / "failure.png"), full_page=True)
            context.tracing.stop(path=str(output / "trace.zip"))
            (output / "browser-errors.txt").write_text("\n".join(errors), encoding="utf-8")
        else:
            context.tracing.stop()
        context.close()
