"""Text-only adapters for the host's Ollama gateway and OpenClaw HTTP API."""

import json
import urllib.request
from urllib.error import HTTPError
from src.core.config import Settings


class GatewayError(RuntimeError):
    pass


class _NoGatewayRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # urllib otherwise forwards authentication headers on redirected requests.
        raise HTTPError(
            request.full_url, code, "Gateway redirects are disabled", headers, response
        )


def _open_gateway_request(request, timeout=60):
    # Keep urllib's default proxy and TLS handlers; replace only redirect policy.
    return urllib.request.build_opener(_NoGatewayRedirect()).open(
        request, timeout=timeout
    )


class GatewayWorker:
    def __init__(self, settings=None):
        self.settings = settings or Settings()
        self.settings.validate()

    def chat(self, messages, *, max_output_tokens=512, timeout_seconds=60):
        if self.settings.mode != "gateway":
            raise GatewayError("Enable gateway mode to call the model")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 4096:
            raise ValueError("Output token budget must be an integer from 1 to 4096")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 180:
            raise ValueError("Gateway timeout must be an integer from 1 to 180 seconds")
        payload = {
            "model": self.settings.model,
            "stream": False,
            "messages": messages,
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.gateway_protocol == "openclaw":
            endpoint = "/v1/chat/completions"
            headers["Authorization"] = "Bearer " + self.settings.gateway_api_key
            # OpenClaw forwards this cap to the provider on a best-effort basis.
            payload.update(temperature=0.1, max_completion_tokens=max_output_tokens)
            # No user/session routing: each call carries only its supplied context.
            # Tool execution remains local; no native function tools are advertised.
        else:
            endpoint = "/api/chat"
            headers["X-API-Key"] = self.settings.gateway_api_key
            payload["options"] = {
                "temperature": 0.1,
                "num_predict": max_output_tokens,
            }
        try:
            request = urllib.request.Request(
                self.settings.gateway_url.rstrip("/") + endpoint,
                data=json.dumps(payload).encode(),
                method="POST",
                headers=headers,
            )
            with _open_gateway_request(request, timeout=timeout_seconds) as response:
                body = json.loads(response.read())
            if self.settings.gateway_protocol == "openclaw":
                choice = body["choices"][0]
                if choice.get("finish_reason") in {"tool_calls", "function_call"}:
                    raise ValueError("Native tool responses are not supported")
                if choice.get("finish_reason") in {"length", "content_filter"}:
                    raise ValueError("The model response did not complete")
                message = choice["message"]
            else:
                if body.get("done_reason") == "length":
                    raise ValueError("The model response did not complete")
                message = body["message"]
            if message.get("tool_calls") or message.get("function_call"):
                raise ValueError("Native tool responses are not supported")
            content = message["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response")
            return content
        except Exception:
            # Upstream errors can contain credentials/source text, even in a traceback.
            raise GatewayError(
                "The model gateway did not return a usable response. Check its configuration and retry."
            ) from None


def generate_text(system, prompt):
    settings = Settings()
    settings.validate()
    if settings.mode == "demo":
        return None
    return GatewayWorker(settings).chat(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        max_output_tokens=4096,
        timeout_seconds=180,
    )
