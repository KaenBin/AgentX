"""Unit tests for core.config."""

from __future__ import annotations

import pytest

from core.config import LLMProvider, Settings


def test_defaults_are_singapore_flavoured() -> None:
    s = Settings(llm_provider=LLMProvider.MOCK)
    assert s.currency == "SGD"
    assert s.timezone == "Asia/Singapore"


def test_log_level_is_normalised() -> None:
    assert Settings(log_level="debug").log_level == "DEBUG"


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(log_level="verbose")


def test_mock_provider_needs_no_key() -> None:
    assert Settings(llm_provider=LLMProvider.MOCK).require_api_key() == ""


def test_real_provider_requires_key() -> None:
    s = Settings(llm_provider=LLMProvider.OPENAI, llm_api_key=None)
    with pytest.raises(ValueError):
        s.require_api_key()


def test_temperature_bounds() -> None:
    with pytest.raises(ValueError):
        Settings(llm_temperature=5.0)
