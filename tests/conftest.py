import pytest


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "demo")
