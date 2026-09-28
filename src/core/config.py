"""Configuration loaded at instance creation, with explicit demo/live modes."""

from dataclasses import dataclass, field
from pathlib import Path
import os
from contextvars import ContextVar
from urllib.parse import urlsplit
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
MODE_OVERRIDE = ContextVar("demo_mode", default=None)


@dataclass(frozen=True)
class Settings:
    gateway_protocol: str = field(
        default_factory=lambda: os.getenv("LLM_GATEWAY_PROTOCOL", "ollama")
    )
    gateway_url: str = field(default_factory=lambda: os.getenv("LLM_GATEWAY_URL", ""))
    gateway_api_key: str = field(
        default_factory=lambda: os.getenv("LLM_GATEWAY_API_KEY", ""), repr=False
    )
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    mode: str = field(
        default_factory=lambda: MODE_OVERRIDE.get() or os.getenv("AGENT_MODE", "demo")
    )
    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("TRAINING_DB", str(ROOT / "data" / "training.db"))
        )
    )
    system_prompt_path: Path = (
        ROOT / "agents" / "system_prompts" / "training_assistant.txt"
    )

    @property
    def live_gateway_configured(self) -> bool:
        return all(
            value.strip()
            for value in (self.gateway_url, self.gateway_api_key, self.model)
        )

    @property
    def gateway_endpoint_path(self) -> str:
        return (
            "/v1/chat/completions"
            if self.gateway_protocol == "openclaw"
            else "/api/chat"
        )

    @property
    def mode_label(self) -> str:
        return "AI coach" if self.mode == "gateway" else "Demo · source excerpts"

    def validate(self):
        if self.gateway_protocol not in {"ollama", "openclaw"}:
            raise ValueError("LLM_GATEWAY_PROTOCOL must be ollama or openclaw")
        if self.mode not in {"demo", "gateway"}:
            raise ValueError("AGENT_MODE must be demo or gateway")
        if self.mode == "gateway" and not self.live_gateway_configured:
            raise ValueError(
                "Gateway mode requires LLM_GATEWAY_URL, LLM_GATEWAY_API_KEY and LLM_MODEL"
            )
        if self.mode == "gateway":
            try:
                url = urlsplit(self.gateway_url)
                valid_url = (
                    url.scheme in {"http", "https"}
                    and bool(url.hostname)
                    and not (url.username or url.password or url.query or url.fragment)
                )
            except ValueError:
                valid_url = False
            if not valid_url:
                raise ValueError(
                    "LLM_GATEWAY_URL must be an HTTP(S) base URL without credentials, query or fragment"
                )
            endpoint_suffixes = (
                ("/v1/chat/completions", "/v1")
                if self.gateway_protocol == "openclaw"
                else ("/api/chat",)
            )
            if url.path.rstrip("/").endswith(endpoint_suffixes):
                raise ValueError(
                    "LLM_GATEWAY_URL must be the base URL, without the API endpoint suffix"
                )
            if self.gateway_protocol == "openclaw" and (
                not self.model.startswith("openclaw/")
                or not self.model.removeprefix("openclaw/").strip()
            ):
                raise ValueError("OpenClaw requires LLM_MODEL=openclaw/<dedicated-agent-id>")
