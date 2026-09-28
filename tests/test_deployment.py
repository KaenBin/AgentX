"""Packaging checks use synthetic files and never load project credentials."""

import io
import os
from pathlib import Path
import zipfile

import pytest

import build_deployment as deployment


@pytest.fixture
def source_tree(tmp_path):
    root = tmp_path / "synthetic-source"
    for name in deployment.PAYLOAD_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("synthetic payload: " + name + "\n").encode())
    (root / ".env.example").write_text("LLM_GATEWAY_API_KEY=\n", encoding="utf-8")
    return root


def test_allowlist_covers_runtime_tests_and_new_release_material():
    names = set(deployment.PAYLOAD_FILES)
    assert len(names) == len(deployment.PAYLOAD_FILES)
    assert {
        "OPENCLAW.md", "DEMO-CHECKLIST.md", "src/check_gateway.py",
        "tests/test_gateway_transport.py", "tests/test_gateway_configuration.py",
        "tests/test_gateway_redirects.py", "tests/test_openclaw_features.py",
        "tests/test_deployment.py", "build_deployment.py",
        "backup-demo.gif",
    } <= names
    suffixes = {".py", ".js", ".cjs", ".css", ".html", ".md", ".txt", ".yml", ".yaml"}
    discovered = {
        path.relative_to(deployment.ROOT).as_posix()
        for folder in ("src", "tests", "agents", ".github")
        for path in (deployment.ROOT / folder).rglob("*")
        if path.is_file() and path.suffix in suffixes
        and not any(part in {"__pycache__", ".pytest_cache"} for part in path.parts)
    }
    assert discovered <= names, "Add new runtime or test files to the explicit package allowlist"


def test_bundle_contains_only_allowlisted_files_without_reading_env(source_tree, tmp_path, monkeypatch):
    excluded = (
        ".env", "data/training.db", "gateway.log", "cookies.json",
        "src/private-notes.txt", "tests/private-session.py",
        "src/__pycache__/worker.pyc", ".pytest_cache/report.md",
    )
    for name in excluded:
        path = source_tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic private data")
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == source_tree / ".env":
            pytest.fail("Packaging attempted to read .env")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    output = tmp_path / "release"
    report = deployment.build_bundle(source_tree, output)
    archive = output / deployment.ARCHIVE_NAME
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(deployment.PAYLOAD_FILES) | {deployment.MANIFEST_NAME}
        assert not set(excluded) & set(bundle.namelist())
    assert deployment.verify_archive(archive)["manifest_verified"] is True
    assert report["sha256"] == deployment.sha256(archive.read_bytes())
    assert (output / deployment.CHECKSUM_NAME).read_text().startswith(report["sha256"] + "  ")


def test_identical_sources_produce_identical_archives_despite_file_times(source_tree, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    deployment.build_bundle(source_tree, first)
    for name in deployment.PAYLOAD_FILES:
        os.utime(source_tree / name, (1_700_000_000, 1_700_000_000))
    deployment.build_bundle(source_tree, second)
    assert (first / deployment.ARCHIVE_NAME).read_bytes() == (second / deployment.ARCHIVE_NAME).read_bytes()
    assert (first / deployment.CHECKSUM_NAME).read_bytes() == (second / deployment.CHECKSUM_NAME).read_bytes()


@pytest.mark.parametrize("existing", [deployment.ARCHIVE_NAME, deployment.CHECKSUM_NAME])
def test_existing_release_or_user_files_are_never_overwritten(source_tree, tmp_path, existing):
    output = tmp_path / "existing-release"
    output.mkdir()
    original = output / existing
    original.write_bytes(b"preserve this existing artifact")
    user_file = output / "notes.txt"
    user_file.write_bytes(b"preserve these notes")
    with pytest.raises(deployment.DeploymentError, match="already exists"):
        deployment.build_bundle(source_tree, output)
    assert original.read_bytes() == b"preserve this existing artifact"
    assert user_file.read_bytes() == b"preserve these notes"
    assert set(path.name for path in output.iterdir()) == {existing, "notes.txt"}


def test_missing_required_document_fails_before_creating_output(source_tree, tmp_path):
    (source_tree / "DEMO-CHECKLIST.md").unlink()
    output = tmp_path / "not-created"
    with pytest.raises(deployment.DeploymentError, match="DEMO-CHECKLIST"):
        deployment.build_bundle(source_tree, output)
    assert not output.exists()


@pytest.mark.parametrize("linked", ["src", "README.md"])
def test_linked_file_or_directory_is_rejected_before_reading(source_tree, monkeypatch, linked):
    original_is_symlink = Path.is_symlink
    target = source_tree / linked
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or original_is_symlink(path))
    with pytest.raises(deployment.DeploymentError, match="Linked payload"):
        deployment.collect_payload(source_tree)


def test_populated_key_example_is_rejected_without_echoing_value(source_tree):
    secret = "synthetic-key-that-must-not-be-reported"
    (source_tree / ".env.example").write_text(f"LLM_GATEWAY_API_KEY={secret}\n")
    with pytest.raises(deployment.DeploymentError) as caught:
        deployment.collect_payload(source_tree)
    assert secret not in str(caught.value)


def test_supplied_credential_copied_into_allowlisted_content_is_rejected(source_tree):
    secret = "synthetic-copied-credential"
    (source_tree / "README.md").write_text(secret)
    with pytest.raises(deployment.DeploymentError) as caught:
        deployment.collect_payload(source_tree, forbidden_values=(secret,))
    assert secret not in str(caught.value)


@pytest.mark.parametrize("mutation", ["changed_content", "extra_env", "missing_file", "duplicate_manifest"])
def test_archive_verifier_rejects_changed_missing_or_extra_content(source_tree, mutation):
    payload = deployment.collect_payload(source_tree)
    if mutation == "changed_content":
        payload["src/agents/worker.py"] = b"different content with a valid ZIP CRC"
    elif mutation == "extra_env":
        payload[".env"] = b"private data"
    elif mutation == "missing_file":
        payload.pop("OPENCLAW.md")
    else:
        payload[deployment.MANIFEST_NAME] += payload[deployment.MANIFEST_NAME].splitlines(keepends=True)[0]
    archive = io.BytesIO(deployment.archive_bytes(payload))
    with pytest.raises(deployment.DeploymentError):
        deployment.verify_archive(archive)
