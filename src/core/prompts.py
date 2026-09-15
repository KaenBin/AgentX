"""Loader for role system prompts stored in ``agents/system_prompts``.

Keeping prompts as version-controlled Markdown (rather than inline strings)
makes them easy to review, diff, and iterate on without touching Python code.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

# repo_root/src/core/prompts.py -> repo_root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPTS_DIR = _REPO_ROOT / "agents" / "system_prompts"


@cache
def load_prompt(role: str) -> str:
    """Load the system prompt for a role (e.g. ``"planner"``, ``"worker"``)."""
    path = _PROMPTS_DIR / f"{role}.md"
    if not path.is_file():
        raise FileNotFoundError(f"No system prompt for role {role!r} at {path}")
    return path.read_text(encoding="utf-8").strip()
