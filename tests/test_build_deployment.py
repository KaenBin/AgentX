"""Check the distributable's content, integrity and isolation from private files."""

import hashlib
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import time
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "AgentX_Learn_Deployment.zip"


@pytest.fixture
def source(tmp_path):
    """Copy distributable source into an isolated checkout-shaped fixture."""
    root = tmp_path / "source"
    root.mkdir()
    for folder in ("src", "tests", "browser_tests", "agents", ".github"):
        shutil.copytree(ROOT / folder, root / folder,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for path in ROOT.iterdir():
        if path.is_file() and (path.suffix in {".md", ".py", ".txt", ".in", ".jpg", ".gif", ".yaml", ".ini", ".ps1"}
                               or path.name in {"Dockerfile", ".env.example", ".gitignore", ".dockerignore"}):
            shutil.copyfile(path, root / path.name)
    return root


def run_build(source, output, *options):
    """Run the actual CLI against a fixture, keeping its diagnostics private."""
    return subprocess.run([sys.executable, *options, str(source / "build_deployment.py"),
                           "--output-dir", str(output)], cwd=source, capture_output=True,
                          text=True, encoding="utf-8", timeout=30)


def test_import_does_not_build_or_overwrite_output(source):
    runpy.run_path(str(source / "build_deployment.py"), run_name="bundle_import")
    assert not (source / "output").exists()


def test_cli_builds_verified_allowlisted_bundle_at_selected_output(source, tmp_path):
    private = b"private-fixture-" + b"do-not-ship"
    for name in (".env", "participant-results.md", "data/private.db", "tmp/private.md",
                 "output/private.md", "skills/private.md", ".codex/private.md",
                 "src/__pycache__/private.py", "tests/.pytest_cache/private.py"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(private)
    (source / ".env").write_text(f"LLM_GATEWAY_API_KEY={private.decode()}\n", encoding="utf-8")
    output = tmp_path / "artifact"
    result = run_build(source, output)
    assert result.returncode == 0, result.stderr
    assert not (source / "output/deployment").exists()
    archive = output / ARCHIVE
    assert (output / "AgentX_Learn_Deployment.sha256").read_text().strip() == (
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + ARCHIVE)
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        assert bundle.testzip() is None
        assert {"src/main.py", "README.md", ".env.example", "DEPENDENCY-ADVISORIES.md",
                "build_deployment.py", "SOURCE-BUNDLE.md",
                "tests/test_build_deployment.py", "MANIFEST.sha256"} <= names
        manifest = dict(line.split("  ", 1)[::-1] for line in bundle.read("MANIFEST.sha256").decode().splitlines())
        assert set(manifest) == names - {"MANIFEST.sha256"}
        for name in names:
            data = bundle.read(name)
            assert private not in data
            if name != "MANIFEST.sha256":
                assert hashlib.sha256(data).hexdigest() == manifest[name]
            if name.endswith(".md"):
                for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", data.decode("utf-8")):
                    if "://" in target or target.startswith(("#", "/", "mailto:")):
                        continue
                    target = target.split("#", 1)[0]
                    if target:
                        resolved = (source / name).parent.joinpath(target).resolve().relative_to(source).as_posix()
                        assert resolved in names, (name, target)


def test_same_source_produces_identical_archives(source, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    assert run_build(source, first).returncode == 0
    # Cross a ZIP timestamp interval so a current-time writer cannot pass by luck.
    time.sleep(2.1)
    assert run_build(source, second).returncode == 0
    assert (first / ARCHIVE).read_bytes() == (second / ARCHIVE).read_bytes()


@pytest.mark.parametrize("optimized", [False, True])
def test_configured_key_in_payload_fails_before_replacing_existing_artifact(source, tmp_path, optimized):
    secret = "fixture-key-that-must-not-appear-in-diagnostics"
    (source / ".env").write_text(f"LLM_GATEWAY_API_KEY='{secret}'\n", encoding="utf-8")
    (source / "README.md").write_text(secret, encoding="utf-8")
    output = tmp_path / "artifact"
    output.mkdir()
    archive = output / ARCHIVE
    checksum = output / "AgentX_Learn_Deployment.sha256"
    archive.write_bytes(b"previous-archive")
    checksum.write_bytes(b"previous-checksum")
    result = run_build(source, output, *(["-O"] if optimized else []))
    assert result.returncode != 0
    assert secret not in result.stdout + result.stderr
    assert archive.read_bytes() == b"previous-archive"
    assert checksum.read_bytes() == b"previous-checksum"


def test_missing_required_file_fails_without_creating_artifact(source, tmp_path):
    (source / "requirements-runtime.txt").unlink()
    output = tmp_path / "artifact"
    result = run_build(source, output)
    assert result.returncode != 0
    assert not output.exists()


def test_default_cli_and_extracted_bundle_can_rebuild(source, tmp_path):
    result = subprocess.run([sys.executable, str(source / "build_deployment.py")],
                            cwd=source, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(source / "output/deployment" / ARCHIVE) as bundle:
        bundle.extractall(extracted)
    output = tmp_path / "rebuilt"
    assert run_build(extracted, output).returncode == 0
    assert (output / ARCHIVE).read_bytes() == (source / "output/deployment" / ARCHIVE).read_bytes()


def test_file_link_outside_source_is_rejected(source, tmp_path):
    private = tmp_path / "external.txt"
    private.write_text("outside source", encoding="utf-8")
    try:
        (source / "src/external.txt").symlink_to(private)
    except OSError:
        pytest.skip("Creating file symlinks requires host privileges")
    output = tmp_path / "artifact"
    assert run_build(source, output).returncode != 0
    assert not output.exists()
