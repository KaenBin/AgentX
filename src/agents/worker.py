import json
import urllib.request

from src.core.config import Settings


class GatewayWorker:
    def __init__(self, settings: Settings):
        self.settings = settings

    def answer(self, question: str, sources: list[dict], system_prompt: str) -> str:
        if not self.settings.live_gateway_configured:
            if not sources:
                return "I cannot determine that from the approved training materials."
            return sources[0]["text"]

        payload = {
            "model": self.settings.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"question": question, "sources": sources})},
            ],
        }
        request = urllib.request.Request(
            self.settings.gateway_url.rstrip("/") + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-API-Key": self.settings.gateway_api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
        return body.get("message", {}).get("content", "")
