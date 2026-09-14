from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    gateway_url: str | None = os.getenv("LLM_GATEWAY_URL")
    gateway_api_key: str | None = os.getenv("LLM_GATEWAY_API_KEY")
    model: str = os.getenv("LLM_MODEL", "")
    system_prompt_path: str = os.getenv(
        "TRAINING_SYSTEM_PROMPT", "agents/system_prompts/training_assistant.txt"
    )

    @property
    def live_gateway_configured(self) -> bool:
        return bool(self.gateway_url and self.gateway_api_key and self.model)
