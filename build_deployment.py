"""Build or verify a reproducible, explicitly allowlisted source deployment ZIP."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parent
ARCHIVE_NAME = "AgentX_Learn_Deployment.zip"
CHECKSUM_NAME = "AgentX_Learn_Deployment.sha256"
MANIFEST_NAME = "MANIFEST.sha256"
# New runtime files and tests must be deliberately added here. Never walk arbitrary
# project content: an unexpected .txt, .py or .md can also contain private data.
PAYLOAD_FILES = tuple("""
.env.example
.gitignore
.github/workflows/test.yml
agents/AGENTS.md
agents/system_prompts/training_assistant.txt
build_deployment.py
backup-demo.gif
requirements.txt
pytest.ini
start.ps1
README.md
DEMO.md
DEMO-CHECKLIST.md
PITCH.md
REHEARSAL.md
DEPLOYMENT.md
OPENCLAW.md
src/__init__.py
src/main.py
src/check_gateway.py
src/validate_live.py
src/agents/__init__.py
src/agents/__main__.py
src/agents/learning_coach.py
src/agents/orchestrator.py
src/agents/protocol.py
src/agents/worker.py
src/core/__init__.py
src/core/config.py
src/core/state.py
src/tools/__init__.py
src/tools/db_queries.py
src/tools/file_ops.py
src/tools/training_tools.py
src/utils/__init__.py
src/utils/logging.py
src/web/app.css
src/web/app.js
src/web/demo.js
src/web/index.html
src/web/readiness.js
src/web/revisions.js
src/workflows/__init__.py
src/workflows/chain.py
src/workflows/change_impact.py
src/workflows/readiness.py
src/workflows/readiness_content.py
src/workflows/rehearsal.py
src/workflows/router.py
src/workflows/sample_course.py
tests/__init__.py
tests/conftest.py
tests/dashboard.test.cjs
tests/test_api.py
tests/test_cli.py
tests/test_deployment.py
tests/test_gateway_configuration.py
tests/test_gateway_redirects.py
tests/test_gateway_transport.py
tests/test_live_validation.py
tests/test_openclaw_features.py
tests/test_readiness.py
tests/test_rehearsal.py
tests/test_revisions.py
tests/test_training.py
tests/test_workflow.py
""".split())


class DeploymentError(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def collect_payload(root, *, forbidden_values=()):
    root = Path(root).resolve()
    payload = {}
    for name in sorted(PAYLOAD_FILES):
        path = root / name
        # Reject both file links and linked directory components before reading.
        for part in (path, *path.parents):
            if part == root:
                break
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise DeploymentError(f"Linked payload path is not allowed: {name}")
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise DeploymentError(f"Required payload file is missing or outside the project: {name}")
        payload[name] = path.read_bytes()
    # This builder never opens .env. The example must remain safe to distribute.
    example = payload[".env.example"].decode("utf-8-sig")
    assignments = re.findall(r"(?m)^\s*LLM_GATEWAY_API_KEY\s*=([^\r\n]*)", example)
    if len(assignments) != 1 or assignments[0].strip() not in {"", "''", '\"\"'}:
        raise DeploymentError("The distributed API-key example must have one empty value")
    for secret in forbidden_values:
        if secret and any(secret.encode("utf-8") in data for data in payload.values()):
            raise DeploymentError("A supplied credential was found in the deployment payload")
    manifest = "".join(f"{sha256(data)}  {name}\n" for name, data in sorted(payload.items()))
    payload[MANIFEST_NAME] = manifest.encode("utf-8")
    return payload


def archive_bytes(payload):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def verify_archive(archive):
    """Verify the complete current allowlist and every uncompressed payload hash."""
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            expected = set(PAYLOAD_FILES) | {MANIFEST_NAME}
            if len(names) != len(expected) or set(names) != expected:
                raise DeploymentError("Archive entries differ from the exact payload allowlist")
            if bundle.testzip() is not None:
                raise DeploymentError("Archive CRC integrity check failed")
            manifest = {}
            for line in bundle.read(MANIFEST_NAME).decode("utf-8").splitlines():
                match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
                if not match or match[2] in manifest:
                    raise DeploymentError("Archive manifest is malformed or contains duplicates")
                manifest[match[2]] = match[1]
            if set(manifest) != set(PAYLOAD_FILES):
                raise DeploymentError("Archive manifest does not cover the exact payload allowlist")
            for name, digest in manifest.items():
                if sha256(bundle.read(name)) != digest:
                    raise DeploymentError(f"Archive content does not match its manifest: {name}")
    except (zipfile.BadZipFile, UnicodeError) as error:
        raise DeploymentError("Archive or manifest could not be decoded") from error
    return {"entries": len(expected), "payload_files": len(PAYLOAD_FILES), "manifest_verified": True}


def build_bundle(root=ROOT, output_dir=None, *, forbidden_values=()):
    root = Path(root).resolve()
    output_dir = Path(output_dir) if output_dir is not None else root / "output" / "deployment"
    archive = output_dir / ARCHIVE_NAME
    checksum = output_dir / CHECKSUM_NAME
    if archive.exists() or checksum.exists():
        raise DeploymentError("Deployment output already exists; choose a new output directory")
    payload = collect_payload(root, forbidden_values=forbidden_values)
    data = archive_bytes(payload)
    report = verify_archive(io.BytesIO(data))
    checksum_data = f"{sha256(data)}  {ARCHIVE_NAME}\n".encode("ascii")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also closes the race after the existence check. Only these
    # two named artifacts are written; prior archives and application data stay intact.
    for path, contents in ((archive, data), (checksum, checksum_data)):
        with path.open("xb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    return report | {"archive": str(archive), "sha256": sha256(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--output-dir", type=Path, help="New destination; existing artifacts are never overwritten")
    options.add_argument("--verify", type=Path, help="Verify an existing archive without building or extracting it")
    args = parser.parse_args()
    try:
        if args.verify:
            report = verify_archive(args.verify)
        else:
            # Optional additional exclusion without loading a local credentials file.
            secret = os.environ.get("LLM_GATEWAY_API_KEY", "")
            report = build_bundle(output_dir=args.output_dir, forbidden_values=(secret,))
        print(json.dumps({"status": "verified", **report}))
        return 0
    except (DeploymentError, OSError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
