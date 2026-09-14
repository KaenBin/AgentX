from pathlib import Path


def read_prompt(path: str) -> str:
    """Read a local prompt file; prompts are configuration, never user input."""
    return Path(path).read_text(encoding="utf-8")
