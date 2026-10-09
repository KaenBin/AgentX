"""Restore a stopped demo's backup as the container's unprivileged user."""

import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile


def restore_backup(
    directory: Path, project: str | None = None, *, compose_files: tuple[Path, ...] = ()
):
    """Restore into empty demo storage only when all app containers are stopped."""
    command = ["docker", "compose"]
    for path in compose_files:
        command += ["-f", str(path.resolve(strict=True))]
    if project:
        command += ["-p", project]
    root = Path(__file__).resolve().parent
    result = subprocess.run(
        [*command, "ps", "--all", "--format", "json", "app"],
        cwd=root, check=True, capture_output=True, text=True, timeout=30,
    )
    output = result.stdout.strip()
    # Compose versions return either a JSON array or one JSON object per line.
    containers = (json.loads(output) if output.startswith("[") else
                  [json.loads(line) for line in output.splitlines()])
    if any(not isinstance(container, dict) or
           container.get("State") not in {"exited", "created"}
           for container in containers):
        raise ValueError("Stop the app before restoring its database")
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
    command += ["run", "--rm", "-T", "--no-deps", "app", "python", "-c",
                "import sys; from pathlib import Path; "
                "from src.tools.restore_files import extract_backup; "
                "extract_backup(sys.stdin.buffer, Path('/app/data'))"]
    subprocess.run(command, input=archive.getvalue(), check=True,
                   cwd=root, timeout=120)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    restore_backup(args.backup)
