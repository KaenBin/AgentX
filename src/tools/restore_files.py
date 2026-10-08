"""Extract a demo backup inside its unprivileged recovery container."""

from pathlib import Path
import tarfile


def extract_backup(stream, destination: Path):
    """Reject existing data before extracting with tar's data-only filter."""
    if any(destination.iterdir()):
        raise ValueError("Restore requires an empty data directory; existing data was not changed")
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        archive.extractall(destination, filter="data")
