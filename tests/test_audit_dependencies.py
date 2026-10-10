"""An advisory audit may pass only with complete coverage of the exact locked pins."""

import json
from pathlib import Path
import subprocess

import pytest


def fixture(root):
    for file, names in [("requirements-runtime.txt", ["app"]),
                        ("requirements.txt", ["app", "test-tool"]),
                        ("requirements-browser.txt", ["app", "test-tool", "browser-tool"])]:
        (root / file).write_text("".join(
            f"{name}==1.0 \\\n    --hash=sha256:{'a' * 64}\n" for name in names), encoding="utf-8")
    return {"dependencies": [{"name": name, "version": "1.0", "vulns": []}
                             for name in ["app", "test-tool", "browser-tool"]], "fixes": []}


def result(payload, code=0):
    return subprocess.CompletedProcess([], code, json.dumps(payload), "private diagnostic")


def test_auditor_packaging_dependencies_are_in_the_reviewed_lock():
    from lock_dependencies import check_locks

    pins = check_locks(Path(__file__).resolve().parents[1])
    assert {"pip-audit", "pip-api", "pip"} <= pins[1].keys()
    assert pins[1]["pip"] == pins[2]["pip"]
    assert "pip-audit" not in pins[0]


def test_complete_audit_records_lock_identity_scopes_and_no_writes(tmp_path, monkeypatch):
    import audit_dependencies as audit

    payload = fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    monkeypatch.setenv("PIP_AUDIT_OUTPUT", str(tmp_path / "unwanted.json"))
    def runner(command, **kwargs):
        assert "--disable-pip" in command and "--no-deps" in command
        assert "--require-hashes" in command and "--fix" not in command
        assert kwargs["capture_output"] is True and kwargs["timeout"] > 0
        assert "PIP_AUDIT_OUTPUT" not in kwargs["env"]
        return result(payload)

    report = audit.run_audit(tmp_path, runner=runner)
    assert report["outcome"] == "passed"
    assert report["service"] == "pypi"
    assert len(report["locks"]) == 3
    assert all(len(lock["sha256"]) == 64 for lock in report["locks"])
    assert report["dependencies"][0]["scopes"] == ["runtime", "development", "browser"]
    assert report["dependencies"][-1]["scopes"] == ["browser"]
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert "private diagnostic" not in json.dumps(report)


def test_known_advisory_fails_and_retains_identifiers_without_description(tmp_path):
    import audit_dependencies as audit

    payload = fixture(tmp_path)
    payload["dependencies"][0]["vulns"] = [{"id": "GHSA-aaaa-bbbb-cccc",
        "aliases": ["CVE-2026-1234"], "fix_versions": ["1.1"], "description": "untrusted private text"}]
    report = audit.run_audit(tmp_path, runner=lambda *a, **k: result(payload, 1))
    assert report["outcome"] == "findings"
    assert report["dependencies"][0]["vulns"] == [{"id": "GHSA-aaaa-bbbb-cccc",
        "aliases": ["CVE-2026-1234"], "fix_versions": ["1.1"]}]
    assert "untrusted private text" not in json.dumps(report)


@pytest.mark.parametrize("defect", ["missing", "extra", "wrong_version", "skipped", "duplicate", "invalid_vulns"])
def test_incomplete_or_invalid_results_cannot_pass(tmp_path, defect):
    import audit_dependencies as audit

    payload = fixture(tmp_path)
    if defect == "missing":
        payload["dependencies"].pop()
    elif defect == "extra":
        payload["dependencies"].append({"name": "unexpected", "version": "1.0", "vulns": []})
    elif defect == "wrong_version":
        payload["dependencies"][0]["version"] = "2.0"
    elif defect == "skipped":
        payload["dependencies"][0] = {"name": "app", "skip_reason": "private error"}
    elif defect == "duplicate":
        payload["dependencies"].append(payload["dependencies"][0])
    else:
        payload["dependencies"][0]["vulns"] = "not a list"
    report = audit.run_audit(tmp_path, runner=lambda *a, **k: result(payload))
    assert report["outcome"] == "error"
    assert "private error" not in json.dumps(report)


@pytest.mark.parametrize("code", [1, 2])
def test_auditor_nonzero_without_findings_is_an_error(tmp_path, code):
    import audit_dependencies as audit

    payload = fixture(tmp_path)
    assert audit.run_audit(tmp_path, runner=lambda *a, **k: result(payload, code))["outcome"] == "error"


def test_invalid_json_and_timeout_are_retained_as_sanitized_errors(tmp_path):
    import audit_dependencies as audit

    fixture(tmp_path)
    invalid = subprocess.CompletedProcess([], 1, "private invalid JSON", "private stderr")
    report = audit.run_audit(tmp_path, runner=lambda *a, **k: invalid)
    assert report["outcome"] == "error"
    assert "private" not in json.dumps(report)
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("private command", 300, output="private stdout")
    assert audit.run_audit(tmp_path, runner=timeout)["outcome"] == "error"


def test_invalid_lock_fails_before_external_auditor(tmp_path):
    import audit_dependencies as audit

    fixture(tmp_path)
    (tmp_path / "requirements-runtime.txt").write_text("app>=1\n", encoding="utf-8")
    report = audit.run_audit(tmp_path, runner=lambda *a, **k: pytest.fail("No auditor on invalid locks"))
    assert report["outcome"] == "error"


def test_cli_preserves_old_report_and_writes_failure_evidence(tmp_path, monkeypatch):
    import audit_dependencies as audit

    fixture(tmp_path)
    monkeypatch.setattr(audit, "__file__", str(tmp_path / "audit_dependencies.py"))
    called = []
    monkeypatch.setattr(audit, "run_audit", lambda root: called.append(root) or {"outcome": "error"})
    path = tmp_path / "report.json"
    assert audit.main(["--output", str(path)]) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["outcome"] == "error"
    original = path.read_bytes()
    assert audit.main(["--output", str(path)]) == 1
    assert path.read_bytes() == original and len(called) == 1
