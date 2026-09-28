import json

import pytest

from src.check_gateway import configuration_report, main
from src.core.config import Settings


def test_preflight_never_sends_requests_or_prints_credentials(monkeypatch, capsys):
    monkeypatch.setenv("LLM_GATEWAY_PROTOCOL", "openclaw")
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://private-host.test")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "do-not-print-this-token")
    monkeypatch.setenv("LLM_MODEL", "openclaw/agentx-training")

    def forbidden_network(*args, **kwargs):
        pytest.fail("Configuration inspection must not call the network")

    monkeypatch.setattr("urllib.request.urlopen", forbidden_network)
    monkeypatch.setattr("src.agents.worker._open_gateway_request", forbidden_network)
    assert main() == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == "configured_not_live_verified"
    assert result["endpoint_path"] == "/v1/chat/completions"
    assert result["network_requests"] == 0
    assert result["live_verified"] is False
    assert "do-not-print-this-token" not in output
    assert "private-host" not in output
    assert "do-not-print-this-token" not in repr(Settings())


def test_missing_settings_block_live_preflight_but_allow_offline_app():
    settings = Settings(mode="demo", gateway_url=" ", gateway_api_key="", model="")
    settings.validate()
    result = configuration_report(settings)
    assert result["status"] == "blocked"
    assert set(result["missing_settings"]) == {
        "LLM_GATEWAY_URL", "LLM_GATEWAY_API_KEY", "LLM_MODEL"
    }


def test_unknown_protocol_fails_before_network_without_echoing_value():
    settings = Settings(gateway_protocol="private-secret-value")
    with pytest.raises(ValueError, match="LLM_GATEWAY_PROTOCOL"):
        settings.validate()
    assert "private-secret-value" not in json.dumps(configuration_report(settings))


def test_existing_config_keeps_ollama_default(monkeypatch):
    monkeypatch.delenv("LLM_GATEWAY_PROTOCOL", raising=False)
    settings = Settings()
    assert settings.gateway_protocol == "ollama"
    assert settings.gateway_endpoint_path == "/api/chat"


@pytest.mark.parametrize("url", [
    "file:///private", "https://user:secret@example.test", "https://example.test?token=secret",
    "https://example.test/v1", "https://example.test/v1/chat/completions",
])
def test_gateway_rejects_wrong_base_url_without_echoing_it(url):
    settings = Settings(mode="gateway", gateway_protocol="openclaw", gateway_url=url, gateway_api_key="fixture", model="openclaw/fixture")
    report = configuration_report(settings)
    assert report["status"] == "blocked"
    assert url not in json.dumps(report)
    assert "secret" not in json.dumps(report)


def test_openclaw_requires_explicit_agent_selector():
    settings = Settings(mode="gateway", gateway_protocol="openclaw", gateway_url="http://127.0.0.1:18789", gateway_api_key="fixture", model="provider-model-name")
    assert configuration_report(settings)["status"] == "blocked"


def test_ollama_preserves_reverse_proxy_base_path():
    settings = Settings(mode="gateway", gateway_protocol="ollama", gateway_url="https://example.test/v1", gateway_api_key="fixture", model="fixture")
    assert configuration_report(settings)["status"] == "configured_not_live_verified"
