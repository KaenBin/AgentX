"""Provider-agnostic LLM interface.

Intended responsibilities:
- Define a common client protocol (chat/completion) across providers.
- Ship an offline mock so the framework runs with no API key.
- Allow swapping OpenAI / Anthropic / local models without touching callers.

Not implemented yet.
"""
