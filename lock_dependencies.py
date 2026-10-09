"""Check or regenerate the demo's three layered, hashed dependency locks."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


LAYERS = (
    ("requirements-runtime.in", "requirements-runtime.txt"),
    ("requirements-dev.in", "requirements.txt"),
    ("requirements-browser.in", "requirements-browser.txt"),
)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
PIN = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][A-Za-z0-9.!+_-]*)"
    r"(?:\s+--hash=sha256:[a-fA-F0-9]{64})+"
)


def normalize(name):
    """Use the same canonical spelling for dots, underscores and hyphens."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_lock(path):
    """Accept the repository's plain exact-pin/hash format, rejecting other directives."""
    pins = {}
    pending = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        continued = line.endswith("\\")
        pending += " " + (line[:-1].rstrip() if continued else line)
        if continued:
            continue
        match = PIN.fullmatch(pending.strip())
        if not match or normalize(match[1]) in pins:
            raise ValueError(f"Invalid, duplicate or unhashed pin in {path.name}")
        pins[normalize(match[1])] = match[2]
        pending = ""
    if pending or not pins:
        raise ValueError(f"Incomplete or empty lock: {path.name}")
    return pins


def check_locks(root):
    """Require every parent pin to appear at exactly the same version in its child."""
    layers = [read_lock(root / output) for _, output in LAYERS]
    for index in range(1, len(layers)):
        for name, version in layers[index - 1].items():
            if layers[index].get(name) != version:
                raise ValueError(f"Shared pin differs or is missing in {LAYERS[index][1]}: {name}")
    return layers


def update_locks(root, *, upgrade=False, packages=(), runner=subprocess.run):
    """Stage a complete candidate, then replace locks with rollback on handled write failures."""
    root = root.resolve()
    layers = check_locks(root)
    targets = []
    for package in packages:
        if not NAME.fullmatch(package):
            raise ValueError("Use an existing package name without a version or URL")
        name = normalize(package)
        owner = next((index for index, pins in enumerate(layers) if name in pins), None)
        if owner is None:
            raise ValueError(f"Package is absent from existing locks: {name}")
        targets.append((owner, name))
    originals = {output: (root / output).read_bytes() for _, output in LAYERS}
    inputs = {source: (root / source).read_bytes() for source, _ in LAYERS}
    with tempfile.TemporaryDirectory(prefix=".dependency-update-", dir=root) as directory:
        stage = Path(directory)
        for source, output in LAYERS:
            (stage / source).write_bytes(inputs[source])
            (stage / output).write_bytes(originals[output])
        env = os.environ.copy()
        mode = "--upgrade" if upgrade else (
            " ".join(f"--package {name}" for _, name in targets) if targets else "--refresh")
        env["CUSTOM_COMPILE_COMMAND"] = f"python lock_dependencies.py {mode}"
        env["PIP_TOOLS_CACHE_DIR"] = str(stage / "cache")
        for index, (source, output) in enumerate(LAYERS):
            command = [sys.executable, "-m", "piptools", "compile", "--generate-hashes",
                       "--no-reuse-hashes",
                       "--no-config", "--no-emit-options", "--strip-extras", "--quiet", "--newline=lf",
                       f"--output-file={output}", source]
            if index:
                command += ["--constraint", LAYERS[index - 1][1]]
            if upgrade:
                command.append("--upgrade")
            else:
                command.append("--no-upgrade")
            for owner, name in targets:
                if owner == index:
                    command += ["--upgrade-package", name]
            runner(command, cwd=stage, env=env, check=True, timeout=600)
        check_locks(stage)
        candidate = {output: (stage / output).read_bytes() for _, output in LAYERS}
        # Detect input or lock edits made during resolution before any replacement.
        if any((root / name).read_bytes() != data for name, data in (originals | inputs).items()):
            raise ValueError("Inputs or lockfiles changed during resolution; candidate was not applied")
        try:
            for output, data in candidate.items():
                (root / output).write_bytes(data)
        except BaseException:
            # Preserve KeyboardInterrupt/SystemExit after attempting to restore the originals.
            for output, data in originals.items():
                (root / output).write_bytes(data)
            raise


def main(argv=None):
    """Check without installation, or explicitly resolve a reviewable dependency change."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate current locks without network or writes")
    mode.add_argument("--refresh", action="store_true", help="Regenerate while preferring existing pins")
    mode.add_argument("--upgrade", action="store_true", help="Resolve all packages within the input bounds")
    mode.add_argument("--package", action="append", default=[], help="Update one existing package; repeatable")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        if args.check:
            check_locks(root)
        else:
            if sys.version_info[:2] != (3, 13):
                raise ValueError("Regenerate locks using Python 3.13, matching CI")
            update_locks(root, upgrade=args.upgrade, packages=args.package)
    except ValueError as error:
        print(f"Dependency maintenance failed: {error}", file=sys.stderr)
        return 1
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Dependency maintenance failed ({type(error).__name__}); inspect the preceding diagnostics.",
              file=sys.stderr)
        return 1
    print("All three dependency locks have hashed pins and consistent shared versions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
