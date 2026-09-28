"""Offline wire-contract tests: all gateway HTTP calls use a fake transport."""

import copy
import io
import json
import traceback
from urllib.error import HTTPError, URLError

import pytest

from src.agents.worker import GatewayError, GatewayWorker, generate_text
from src.core.config import Settings


class Response:
    def __init__(self, body):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def settings(protocol, **overrides):
    values = {
        "mode": "gateway",
        "gateway_protocol": protocol,
        "gateway_url": "https://example.test/",
        "gateway_api_key": "synthetic-secret",
        "model": "openclaw/agentx-training" if protocol == "openclaw" else "sonnet",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture(autouse=True)
def no_real_gateway_requests(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("A gateway test attempted an unstubbed HTTP request")

    monkeypatch.setattr("src.agents.worker._open_gateway_request", blocked)


def test_ollama_wire_contract_is_preserved(monkeypatch):
    messages = [{"role": "system", "content": "synthetic instructions"}]
    captured = []

    def transport(request, timeout):
        captured.append(request)
        assert request.get_method() == "POST"
        assert request.full_url == "https://example.test/api/chat"
        assert request.get_header("Content-type") == "application/json"
        assert request.get_header("X-api-key") == "synthetic-secret"
        assert request.get_header("Authorization") is None
        assert timeout == 60
        assert json.loads(request.data) == {
            "model": "sonnet",
            "stream": False,
            "messages": messages,
            "options": {"temperature": 0.1, "num_predict": 512},
        }
        return Response({"message": {"content": '{"answer":"hello"}'}})

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    assert GatewayWorker(settings("ollama")).chat(messages) == '{"answer":"hello"}'
    assert len(captured) == 1


def test_openclaw_uses_bearer_chat_completions_without_session_or_native_tools(monkeypatch):
    messages = [
        {"role": "system", "content": "return application JSON"},
        {"role": "user", "content": "synthetic question"},
    ]
    before = copy.deepcopy(messages)
    captured = []

    def transport(request, timeout):
        captured.append(request)
        assert request.get_method() == "POST"
        assert request.full_url == "https://example.test/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer synthetic-secret"
        assert request.get_header("X-api-key") is None
        assert request.get_header("Content-type") == "application/json"
        assert not any("session" in name.lower() for name, _ in request.header_items())
        assert timeout == 60
        assert json.loads(request.data) == {
            "model": "openclaw/agentx-training",
            "stream": False,
            "messages": messages,
            "temperature": 0.1,
            "max_completion_tokens": 512,
        }
        return Response(
            {
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"answer":"hello"}'}}
                ]
            }
        )

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    assert GatewayWorker(settings("openclaw")).chat(messages) == '{"answer":"hello"}'
    assert messages == before
    assert len(captured) == 1


def test_openclaw_repeated_calls_do_not_reuse_or_accumulate_remote_context(monkeypatch):
    payloads = []

    def transport(request, timeout):
        payloads.append(json.loads(request.data))
        assert not any("session" in name.lower() for name, _ in request.header_items())
        return Response(
            {
                "id": "remote-session-must-not-be-reused",
                "choices": [{"message": {"content": "ok"}}],
            }
        )

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    worker = GatewayWorker(settings("openclaw"))
    worker.chat([{"role": "user", "content": "first learner"}])
    worker.chat([{"role": "user", "content": "second learner"}])
    assert len(payloads) == 2
    assert payloads[0]["messages"] == [{"role": "user", "content": "first learner"}]
    assert payloads[1]["messages"] == [{"role": "user", "content": "second learner"}]
    assert all("user" not in payload and "session" not in payload for payload in payloads)
    assert "remote-session-must-not-be-reused" not in json.dumps(payloads)


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("content", [None, "", " \n\t", 123, [], {"text": "not a string"}])
def test_gateway_rejects_empty_or_nontext_content(monkeypatch, protocol, content):
    message = {"content": content}
    body = {"message": message} if protocol == "ollama" else {"choices": [{"message": message}]}
    calls = []

    def transport(request, timeout):
        calls.append(request)
        return Response(body)

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    with pytest.raises(GatewayError, match="usable response"):
        GatewayWorker(settings(protocol)).chat([])
    assert len(calls) == 1


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("body", [b"not json", b"null", b"[]", b"{}"])
def test_gateway_rejects_invalid_envelopes_without_retry(monkeypatch, protocol, body):
    calls = []

    def transport(request, timeout):
        calls.append(request)
        return Response(body)

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    with pytest.raises(GatewayError):
        GatewayWorker(settings(protocol)).chat([])
    assert len(calls) == 1


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
def test_truncated_output_is_rejected_even_if_content_looks_like_valid_json(monkeypatch, protocol):
    message = {"content": '{"answer":"partial result"}'}
    body = (
        {"message": message, "done_reason": "length"}
        if protocol == "ollama"
        else {"choices": [{"message": message, "finish_reason": "length"}]}
    )
    monkeypatch.setattr("src.agents.worker._open_gateway_request", lambda *args, **kwargs: Response(body))
    with pytest.raises(GatewayError):
        GatewayWorker(settings(protocol)).chat([])


@pytest.mark.parametrize(
    "choice",
    [
        {"finish_reason": "tool_calls", "message": {"content": None}},
        {"finish_reason": "function_call", "message": {"content": "commentary"}},
        {"message": {"content": None, "tool_calls": [{"function": {"name": "publish_course"}}]}},
        {
            "message": {
                "content": '{"answer":"done"}',
                "tool_calls": [{"function": {"name": "publish_course"}}],
            }
        },
        {"message": {"content": '{"answer":"done"}', "function_call": {"name": "publish_course"}}},
    ],
)
def test_openclaw_native_tool_responses_are_not_treated_as_application_json(monkeypatch, choice):
    monkeypatch.setattr(
        "src.agents.worker._open_gateway_request",
        lambda *args, **kwargs: Response({"choices": [choice]}),
    )
    with pytest.raises(GatewayError, match="usable response"):
        GatewayWorker(settings("openclaw")).chat([])


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("failure_kind", ["http", "network", "timeout", "json"])
def test_gateway_failures_redact_messages_and_tracebacks_without_retry(
    monkeypatch, protocol, failure_kind, capsys
):
    secret = "synthetic-private-upstream-detail"
    calls = []

    def transport(request, timeout):
        calls.append(request)
        if failure_kind == "http":
            raise HTTPError(
                "https://example.test/" + secret,
                401,
                secret,
                {},
                io.BytesIO(secret.encode()),
            )
        if failure_kind == "network":
            raise URLError(secret)
        if failure_kind == "timeout":
            raise TimeoutError(secret)
        return Response(("{bad json " + secret).encode())

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    with pytest.raises(GatewayError) as caught:
        GatewayWorker(settings(protocol)).chat([])
    assert len(calls) == 1
    assert secret not in str(caught.value)
    assert secret not in "".join(traceback.format_exception(caught.value))
    assert "synthetic-secret" not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    output = capsys.readouterr()
    assert output.out == output.err == ""


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
def test_demo_mode_never_calls_a_gateway(protocol):
    with pytest.raises(GatewayError, match="Enable gateway mode"):
        GatewayWorker(settings(protocol, mode="demo")).chat([])


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("budget", [0, -1, 4097, True, 1.5, "512", None])
def test_invalid_output_budgets_fail_before_network(protocol, budget):
    with pytest.raises(ValueError, match="Output token budget"):
        GatewayWorker(settings(protocol)).chat([], max_output_tokens=budget)


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("timeout", [0, -1, 181, True, False, 1.5, "60", None])
def test_invalid_timeouts_fail_before_network(protocol, timeout):
    with pytest.raises(ValueError, match="Gateway timeout"):
        GatewayWorker(settings(protocol)).chat([], timeout_seconds=timeout)


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("timeout", [1, 180])
def test_timeout_bounds_are_forwarded_once(monkeypatch, protocol, timeout):
    calls = []

    def transport(request, timeout):
        calls.append(timeout)
        message = {"content": "ok"}
        return Response(
            {"message": message} if protocol == "ollama"
            else {"choices": [{"message": message}]}
        )

    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    assert GatewayWorker(settings(protocol)).chat([], timeout_seconds=timeout) == "ok"
    assert calls == [timeout]


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
def test_course_generation_uses_larger_budget_and_timeout_without_changing_chat_defaults(
    monkeypatch, protocol
):
    configured = settings(protocol)
    budgets = []
    timeouts = []
    prompts = []

    def transport(request, timeout):
        timeouts.append(timeout)
        payload = json.loads(request.data)
        prompts.append(payload["messages"])
        if protocol == "openclaw":
            budgets.append(payload["max_completion_tokens"])
            return Response({"choices": [{"message": {"content": "{}"}}]})
        budgets.append(payload["options"]["num_predict"])
        return Response({"message": {"content": "{}"}})

    monkeypatch.setattr("src.agents.worker.Settings", lambda: configured)
    monkeypatch.setattr("src.agents.worker._open_gateway_request", transport)
    assert generate_text("synthetic course schema", "synthetic source") == "{}"
    assert GatewayWorker(configured).chat([]) == "{}"
    assert budgets == [4096, 512]
    assert timeouts == [180, 60]
    assert prompts[0] == [
        {"role": "system", "content": "synthetic course schema"},
        {"role": "user", "content": "synthetic source"},
    ]
