"""Restore a stopped demo's backup as the container's unprivileged user."""

import argparse
import io
from pathlib import Path
import subprocess
import tarfile


def restore_backup(directory: Path, project: str | None = None):
    directory = directory.resolve(strict=True)
    if not (directory / "training.db").is_file():
        raise ValueError("Backup must contain training.db")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as bundle:
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Backups must not contain symbolic links")
            if path.is_file():
                bundle.add(path, arcname=path.relative_to(directory).as_posix(), recursive=False)
    command = ["docker", "compose"]
    if project:
        command += ["-p", project]
    command += ["run", "--rm", "-T", "--no-deps", "app", "python", "-c",
                "import sys,tarfile; tarfile.open(fileobj=sys.stdin.buffer,mode='r|').extractall('/app/data',filter='data')"]
    subprocess.run(command, input=archive.getvalue(), check=True,
                   cwd=Path(__file__).resolve().parent, timeout=120)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    restore_backup(args.backup)
