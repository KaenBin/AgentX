"""Protect layered dependency updates from drift and partial resolver failure."""

from pathlib import Path
import subprocess

import pytest


LOCKS = ("requirements-runtime.txt", "requirements.txt", "requirements-browser.txt")
INPUTS = ("requirements-runtime.in", "requirements-dev.in", "requirements-browser.in")


def lock(*pins):
    return "".join(f"{name}=={version} \\\n    --hash=sha256:{'a' * 64}\n" for name, version in pins)


def fixture(root):
    for name in INPUTS:
        (root / name).write_text("fixture\n", encoding="utf-8")
    for name, pins in zip(LOCKS, [(("app", "1.0"),), (("app", "1.0"), ("test", "2.0")),
                                (("app", "1.0"), ("test", "2.0"), ("browser", "3.0"))]):
        (root / name).write_text(lock(*pins), encoding="utf-8")
    return {name: (root / name).read_bytes() for name in LOCKS}


def test_check_existing_repository_locks_without_writes():
    import lock_dependencies as maintenance

    root = Path(__file__).resolve().parents[1]
    before = {name: (root / name).read_bytes() for name in LOCKS}
    maintenance.check_locks(root)
    assert before == {name: (root / name).read_bytes() for name in LOCKS}


@pytest.mark.parametrize("bad", [
    "app>=1\n", "app==1.0\n", "app==1.0 \\\n    --hash=sha256:nope\n",
    lock(("app", "1.0")) + lock(("app", "2.0")),
    "--extra-index-url https://credential@example.invalid\n" + lock(("app", "1.0")),
])
def test_reject_unpinned_unhashed_duplicate_or_index_content(tmp_path, bad):
    import lock_dependencies as maintenance

    fixture(tmp_path)
    (tmp_path / LOCKS[0]).write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError):
        maintenance.check_locks(tmp_path)


@pytest.mark.parametrize("bad", [lock(("app", "9.0"), ("test", "2.0")), lock(("test", "2.0"))])
def test_shared_runtime_pin_cannot_drift_or_disappear(tmp_path, bad):
    import lock_dependencies as maintenance

    fixture(tmp_path)
    (tmp_path / LOCKS[1]).write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError):
        maintenance.check_locks(tmp_path)


def test_compile_in_order_and_commit_only_complete_valid_layers(tmp_path):
    import lock_dependencies as maintenance

    before = fixture(tmp_path)
    seen = []

    def compile_fixture(command, *, cwd, **kwargs):
        index = len(seen)
        assert {name: (tmp_path / name).read_bytes() for name in LOCKS} == before
        assert cwd != tmp_path
        assert "--generate-hashes" in command and "--no-config" in command
        assert "--upgrade" in command
        assert kwargs["check"] is True and kwargs["timeout"] > 0
        if index:
            assert maintenance.read_lock(cwd / LOCKS[index - 1])["app"] == "1.1"
        pins = [("app", "1.1"), ("test", "2.1"), ("browser", "3.1")][:index + 1]
        (cwd / LOCKS[index]).write_text(lock(*pins), encoding="utf-8")
        seen.append(command)

    maintenance.update_locks(tmp_path, upgrade=True, runner=compile_fixture)
    assert len(seen) == 3
    maintenance.check_locks(tmp_path)
    assert maintenance.read_lock(tmp_path / LOCKS[2])["browser"] == "3.1"
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted((*LOCKS, *INPUTS))


@pytest.mark.parametrize("failure", ["resolver", "invalid"])
def test_failed_candidate_keeps_all_original_bytes(tmp_path, failure):
    import lock_dependencies as maintenance

    before = fixture(tmp_path)
    seen = []

    def compile_fixture(command, *, cwd, **kwargs):
        index = len(seen)
        seen.append(command)
        if index == 1 and failure == "resolver":
            raise subprocess.CalledProcessError(1, command)
        pins = [("app", "1.1"), ("test", "2.0"), ("browser", "3.0")][:index + 1]
        if index == 2:
            pins[0] = ("app", "9.0")
        (cwd / LOCKS[index]).write_text(lock(*pins), encoding="utf-8")

    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        maintenance.update_locks(tmp_path, runner=compile_fixture)
    assert before == {name: (tmp_path / name).read_bytes() for name in LOCKS}
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted((*LOCKS, *INPUTS))


def test_targeted_update_releases_pin_only_in_first_owning_layer(tmp_path):
    import lock_dependencies as maintenance

    fixture(tmp_path)
    seen = []
    maintenance.update_locks(tmp_path, packages=["app", "browser"],
                             runner=lambda command, **kwargs: seen.append(command))
    assert seen[0].count("--upgrade-package") == 1 and "app" in seen[0]
    assert "--upgrade-package" not in seen[1]
    assert seen[2].count("--upgrade-package") == 1 and "browser" in seen[2]


def test_unknown_target_rejected_before_compiler_or_writes(tmp_path):
    import lock_dependencies as maintenance

    before = fixture(tmp_path)
    with pytest.raises(ValueError):
        maintenance.update_locks(tmp_path, packages=["typo"],
                                 runner=lambda *a, **k: pytest.fail("Compiler must not run"))
    assert before == {name: (tmp_path / name).read_bytes() for name in LOCKS}


def test_write_failure_restores_already_replaced_locks(tmp_path, monkeypatch):
    import lock_dependencies as maintenance

    before = fixture(tmp_path)
    original = Path.write_bytes
    failed = False

    def fail_once(path, data):
        nonlocal failed
        if path == tmp_path / LOCKS[1] and not failed:
            failed = True
            raise OSError("simulated write failure")
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_once)
    def compile_fixture(command, *, cwd, **kwargs):
        for name in LOCKS:
            original(cwd / name, (cwd / name).read_bytes().replace(b"app==1.0", b"app==1.1"))

    with pytest.raises(OSError):
        maintenance.update_locks(tmp_path, runner=compile_fixture)
    assert before == {name: (tmp_path / name).read_bytes() for name in LOCKS}


@pytest.mark.parametrize("edited", [INPUTS[0], LOCKS[0]])
def test_concurrent_edit_is_preserved_and_candidate_is_not_applied(tmp_path, edited):
    import lock_dependencies as maintenance

    before = fixture(tmp_path)
    def compile_fixture(command, *, cwd, **kwargs):
        (tmp_path / edited).write_text("concurrent human edit\n", encoding="utf-8")

    with pytest.raises(ValueError, match="changed during resolution"):
        maintenance.update_locks(tmp_path, runner=compile_fixture)
    assert (tmp_path / edited).read_text(encoding="utf-8") == "concurrent human edit\n"
    for name in LOCKS:
        if name != edited:
            assert (tmp_path / name).read_bytes() == before[name]


def test_cli_reports_the_invalid_lock_without_network(tmp_path, monkeypatch, capsys):
    import lock_dependencies as maintenance

    fixture(tmp_path)
    (tmp_path / LOCKS[0]).write_text("app>=1\n", encoding="utf-8")
    monkeypatch.setattr(maintenance, "__file__", str(tmp_path / "lock_dependencies.py"))
    assert maintenance.main(["--check"]) == 1
    assert "requirements-runtime.txt" in capsys.readouterr().err
