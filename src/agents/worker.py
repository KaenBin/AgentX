"""Ollama /api/chat adapter for the host's Bedrock gateway."""

import json
import urllib.request
from src.core.config import Settings


class GatewayError(RuntimeError):
    pass


class GatewayWorker:
    def __init__(self, settings=None):
        self.settings = settings or Settings()
        self.settings.validate()

    def chat(self, messages):
        if self.settings.mode != "gateway":
            raise GatewayError("Enable gateway mode to call the model")
        payload = {
            "model": self.settings.model,
            "stream": False,
            "messages": messages,
            "options": {"temperature": 0.1, "num_predict": 512},
        }
        request = urllib.request.Request(
            self.settings.gateway_url.rstrip("/") + "/api/chat",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.settings.gateway_api_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read())
            content = body["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response")
            return content
        except Exception as exc:
            # Avoid returning upstream bodies, which can contain credentials or source text.
            raise GatewayError(
                "The model gateway did not return a usable response. Check its configuration and retry."
            ) from exc


def generate_text(system, prompt):
    settings = Settings()
    settings.validate()
    if settings.mode == "demo":
        return None
    return GatewayWorker(settings).chat(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    )
