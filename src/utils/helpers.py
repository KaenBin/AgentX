"""Small, dependency-free helper functions used across the codebase."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import TypeVar

T = TypeVar("T")

_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{6,})"
)


def slugify(text: str) -> str:
    """Convert arbitrary text into a filesystem/URL-friendly slug."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def truncate(text: str, limit: int = 200, suffix: str = "…") -> str:
    """Truncate text to ``limit`` characters, appending a suffix if cut."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(suffix))] + suffix


def chunk(items: list[T], size: int) -> list[list[T]]:
    """Split a list into consecutive chunks of at most ``size`` items."""
    if size <= 0:
        raise ValueError("size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]


def format_sgd(amount: float | int | str | Decimal) -> str:
    """Format a monetary amount as Singapore dollars, e.g. ``S$1,234.50``."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"S${value:,.2f}"


def redact_secrets(text: str) -> str:
    """Mask anything that looks like a credential before logging user data."""
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=***REDACTED***", text)
