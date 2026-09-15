"""Application configuration.

Configuration is centralised here and loaded from environment variables (and an
optional ``.env`` file) using ``pydantic-settings``. Every setting is prefixed
with ``AGENTX_`` and validated once at startup so the rest of the codebase can
rely on a single, typed ``Settings`` object rather than reading ``os.environ``
directly.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM backends. ``MOCK`` requires no network or API key."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class LogFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


class Settings(BaseSettings):
    """Typed, validated application settings.

    Prefer ``get_settings()`` over instantiating this directly so the parsed
    configuration is cached for the lifetime of the process.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENTX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---------------------------------------------------------------
    llm_provider: LLMProvider = LLMProvider.MOCK
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # --- Agent safety rails ------------------------------------------------
    max_agent_steps: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=25, ge=1, le=500)

    # --- Sandboxing / data -------------------------------------------------
    sandbox_root: Path = Path("./sandbox_workspace")
    database_url: str = "sqlite:///./sandbox_workspace/sme.db"

    # --- Logging -----------------------------------------------------------
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.TEXT

    # --- Locale (Singapore SME defaults) -----------------------------------
    timezone: str = "Asia/Singapore"
    currency: str = "SGD"

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got {value!r}")
        return level

    def require_api_key(self) -> str:
        """Return the API key or raise if the provider needs one but it is missing."""
        if self.llm_provider is LLMProvider.MOCK:
            return ""
        if not self.llm_api_key:
            raise ValueError(
                f"AGENTX_LLM_API_KEY is required for provider {self.llm_provider.value!r}"
            )
        return self.llm_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""
    return Settings()
