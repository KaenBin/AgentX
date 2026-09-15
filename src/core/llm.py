"""Provider-agnostic LLM interface.

The rest of the framework talks to an ``LLMClient`` protocol rather than any
specific vendor SDK. This keeps SMEs free to switch between OpenAI, Anthropic,
or a local/self-hosted model without touching orchestration code. A
``MockLLMClient`` ships by default so the framework — and its tests — run
offline with no API key.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import LLMProvider, Settings
from core.state import Message, Role


@runtime_checkable
class LLMClient(Protocol):
    """Minimal contract every provider adapter must satisfy."""

    def complete(self, messages: list[Message], **kwargs: object) -> str:
        """Return the assistant's text completion for the given transcript."""
        ...


class MockLLMClient:
    """Deterministic, offline client for development and tests.

    It echoes a compact, predictable response derived from the last user
    message so higher-level logic can be exercised without a network call.
    """

    def __init__(self, canned: dict[str, str] | None = None) -> None:
        self._canned = canned or {}

    def complete(self, messages: list[Message], **kwargs: object) -> str:
        last_user = next(
            (m for m in reversed(messages) if m.role is Role.USER),
            None,
        )
        prompt = last_user.content if last_user else ""
        for needle, response in self._canned.items():
            if needle.lower() in prompt.lower():
                return response
        return f"[mock] processed: {prompt[:200]}"


class _RetryingClient:
    """Wraps a real provider callable with exponential-backoff retries."""

    def __init__(self, model: str, temperature: float, call):  # noqa: ANN001
        self._model = model
        self._temperature = temperature
        self._call = call

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def complete(self, messages: list[Message], **kwargs: object) -> str:
        payload = [{"role": m.role.value, "content": m.content} for m in messages]
        return self._call(self._model, self._temperature, payload, **kwargs)


def _build_openai(settings: Settings) -> LLMClient:
    from openai import OpenAI  # imported lazily; optional dependency

    client = OpenAI(api_key=settings.require_api_key())

    def call(model, temperature, payload, **kwargs):  # noqa: ANN001, ANN003
        resp = client.chat.completions.create(
            model=model, temperature=temperature, messages=payload
        )
        return resp.choices[0].message.content or ""

    return _RetryingClient(settings.llm_model, settings.llm_temperature, call)


def _build_anthropic(settings: Settings) -> LLMClient:
    import anthropic  # imported lazily; optional dependency

    client = anthropic.Anthropic(api_key=settings.require_api_key())

    def call(model, temperature, payload, **kwargs):  # noqa: ANN001, ANN003
        system = "\n".join(m["content"] for m in payload if m["role"] == "system")
        turns = [m for m in payload if m["role"] != "system"]
        resp = client.messages.create(
            model=model,
            temperature=temperature,
            system=system or None,
            max_tokens=1024,
            messages=turns,
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    return _RetryingClient(settings.llm_model, settings.llm_temperature, call)


def build_llm_client(settings: Settings) -> LLMClient:
    """Factory that returns the client matching ``settings.llm_provider``."""
    if settings.llm_provider is LLMProvider.MOCK:
        return MockLLMClient()
    if settings.llm_provider is LLMProvider.OPENAI:
        return _build_openai(settings)
    if settings.llm_provider is LLMProvider.ANTHROPIC:
        return _build_anthropic(settings)
    raise ValueError(f"Unsupported provider: {settings.llm_provider!r}")
