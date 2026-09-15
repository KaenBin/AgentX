"""Unit tests for utils.helpers."""

from __future__ import annotations

import pytest

from utils.helpers import chunk, format_sgd, redact_secrets, slugify, truncate


def test_slugify() -> None:
    assert slugify("  Ah Seng Trading Pte Ltd! ") == "ah-seng-trading-pte-ltd"


def test_truncate() -> None:
    assert truncate("hello world", 5) == "hell…"
    assert truncate("short", 50) == "short"
    assert truncate("x", 0) == ""


def test_chunk() -> None:
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    with pytest.raises(ValueError):
        chunk([1], 0)


def test_format_sgd() -> None:
    assert format_sgd(1234.5) == "S$1,234.50"
    assert format_sgd("0.1") == "S$0.10"


def test_redact_secrets() -> None:
    redacted = redact_secrets('api_key="abcdef123456" other text')
    assert "abcdef123456" not in redacted
    assert "REDACTED" in redacted
