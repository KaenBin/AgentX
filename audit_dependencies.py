"""Retain complete, dated PyPI advisory evidence for the demo's locked packages."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from lock_dependencies import LAYERS, check_locks, normalize


SCOPES = ("runtime", "development", "browser")


def timestamp():
    """Record UTC so evidence from different machines can be compared."""
    return datetime.now(timezone.utc).isoformat()


def source_identity(root):
    """Identify a checkout when available; lock hashes also support extracted bundles."""
    command = ["git", "-c", f"safe.directory={root.as_posix()}"]
    try:
        tracked = subprocess.run(command + ["ls-files", "--error-unmatch", "--", "audit_dependencies.py",
                                 *(output for _, output in LAYERS)], cwd=root,
                                 capture_output=True, timeout=10)
        if tracked.returncode:
            return {"commit": None, "tracked_changes": None}
        result = subprocess.run(command + ["rev-parse", "HEAD"], cwd=root,
                                capture_output=True, text=True, timeout=10)
        if result.returncode or not re.fullmatch(r"[a-f0-9]{40,64}", result.stdout.strip()):
            return {"commit": None, "tracked_changes": None}
        dirty = subprocess.run(command + ["diff", "HEAD", "--quiet"], cwd=root,
                               capture_output=True, timeout=10)
        return {"commit": result.stdout.strip(), "tracked_changes": dirty.returncode != 0}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "tracked_changes": None}


def advisory_strings(value, pattern):
    """Retain bounded identifiers/versions, excluding free-form advisory text."""
    if not isinstance(value, list) or any(
            not isinstance(item, str) or len(item) > 128 or not re.fullmatch(pattern, item)
            for item in value):
        raise ValueError("Invalid advisory fields")
    return value


def validate_results(payload, pins):
    """Require exactly one audited entry for every expected package and version."""
    if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
        raise ValueError("Invalid audit response")
    if payload.get("fixes"):
        raise ValueError("Unexpected automatic fixes")
    found = {}
    for entry in payload["dependencies"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ValueError("Invalid dependency entry")
        name = normalize(entry["name"])
        if name in found or name not in pins[-1] or entry.get("version") != pins[-1][name]:
            raise ValueError("Unexpected dependency or version")
        if "skip_reason" in entry or not isinstance(entry.get("vulns"), list):
            raise ValueError("Dependency not fully audited")
        vulns = []
        for vuln in entry["vulns"]:
            if not isinstance(vuln, dict):
                raise ValueError("Invalid advisory")
            ids = advisory_strings([vuln.get("id")], r"[A-Za-z0-9_.-]+")
            vulns.append({"id": ids[0],
                          "aliases": advisory_strings(vuln.get("aliases", []), r"[A-Za-z0-9_.-]+"),
                          "fix_versions": advisory_strings(vuln.get("fix_versions", []), r"[0-9][A-Za-z0-9.!+_-]*")})
        found[name] = {"name": name, "version": entry["version"], "vulns": vulns,
                       "scopes": [scope for scope, layer in zip(SCOPES, pins) if name in layer]}
    if set(found) != set(pins[-1]):
        raise ValueError("Incomplete audit coverage")
    return [found[name] for name in pins[-1]]


def run_audit(root, *, runner=subprocess.run):
    """Audit immutable lock snapshots; classify findings separately from execution errors."""
    root = root.resolve()
    try:
        tool_version = version("pip-audit")
    except PackageNotFoundError:
        tool_version = None
    report = {"schema_version": 1, "started_at": timestamp(), "finished_at": None,
              "service": "pypi", "tool": {"name": "pip-audit", "version": tool_version},
              "source": source_identity(root), "locks": [], "dependencies": [], "outcome": "error"}
    try:
        snapshots = {output: (root / output).read_bytes() for _, output in LAYERS}
        report["locks"] = [{"file": name, "sha256": hashlib.sha256(data).hexdigest()}
                           for name, data in snapshots.items()]
        with tempfile.TemporaryDirectory(prefix="agentx-advisories-") as directory:
            stage = Path(directory)
            for name, data in snapshots.items():
                (stage / name).write_bytes(data)
            try:
                pins = check_locks(stage)
            except ValueError:
                report["reason"] = "invalid_locks"
                return report
            command = [sys.executable, "-m", "pip_audit", "--requirement", str(stage / LAYERS[-1][1]),
                       "--no-deps", "--disable-pip", "--require-hashes", "--format", "json",
                       "--vulnerability-service", "pypi", "--desc", "off", "--aliases", "on",
                       "--progress-spinner", "off", "--timeout", "15", "--cache-dir", str(stage / "cache")]
            env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PIP_AUDIT_")}
            result = runner(command, env=env, capture_output=True, text=True, encoding="utf-8",
                            timeout=300, stdin=subprocess.DEVNULL)
            dependencies = validate_results(json.loads(result.stdout), pins)
            has_findings = any(entry["vulns"] for entry in dependencies)
            if result.returncode != (1 if has_findings else 0):
                report["reason"] = "auditor_exit_mismatch"
                return report
            report["dependencies"] = dependencies
            report["outcome"] = "findings" if has_findings else "passed"
    except subprocess.TimeoutExpired:
        report["reason"] = "auditor_timeout"
    except (ValueError, TypeError):
        report["reason"] = "invalid_audit_response"
    except (OSError, subprocess.SubprocessError):
        report["reason"] = "audit_execution_failed"
    finally:
        report["finished_at"] = timestamp()
    return report


def main(argv=None):
    """Write a new report and fail on advisories or incomplete audit execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New JSON report filename")
    args = parser.parse_args(argv)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            report = run_audit(Path(__file__).resolve().parent)
            json.dump(report, stream, indent=2)
            stream.write("\n")
    except OSError:
        print("Cannot create a new audit report; choose an unused writable filename.", file=sys.stderr)
        return 1
    print(f"Dependency advisory audit: {report['outcome']}.")
    return 0 if report["outcome"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
