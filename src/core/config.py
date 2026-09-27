"""Configuration loaded at instance creation, with explicit demo/live modes."""

from dataclasses import dataclass, field
from pathlib import Path
import os
from contextvars import ContextVar
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
MODE_OVERRIDE = ContextVar("demo_mode", default=None)


@dataclass(frozen=True)
class Settings:
    gateway_url: str = field(default_factory=lambda: os.getenv("LLM_GATEWAY_URL", ""))
    gateway_api_key: str = field(
        default_factory=lambda: os.getenv("LLM_GATEWAY_API_KEY", "")
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
        return bool(self.gateway_url and self.gateway_api_key and self.model)

    @property
    def mode_label(self) -> str:
        return "AI coach" if self.mode == "gateway" else "Demo · source excerpts"

    def validate(self):
        if self.mode not in {"demo", "gateway"}:
            raise ValueError("AGENT_MODE must be demo or gateway")
        if self.mode == "gateway" and not self.live_gateway_configured:
            raise ValueError(
                "Gateway mode requires LLM_GATEWAY_URL, LLM_GATEWAY_API_KEY and LLM_MODEL"
            )
