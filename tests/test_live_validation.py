import json

import pytest

from src.core.config import Settings
from src.tools import db_queries as db
from src.validate_live import check, main


class ScriptedWorker:
    def chat(self, messages):
        if "Select the most useful" in messages[0]["content"]:
            state = json.loads(messages[1]["content"])
            choice = next(a for a in state["eligible_actions"] if a["kind"] == "lesson")
            return json.dumps(
                {
                    "tool": "select_approved_activity",
                    "args": {
                        "session_id": state["session_id"],
                        "activity_id": choice["activity_id"],
                    },
                }
            )
        context = json.loads(messages[1]["content"])
        if len(messages) == 2:
            return json.dumps(
                {"tool": "retrieve_sources", "args": {"query": context["question"]}}
            )
        return json.dumps(
            {
                "answer": (
                    "Ask the supplier for a duplicate receipt. [1]"
                    if "receipt" in context["question"]
                    else "Ask your trainer."
                )
            }
        )


def settings():
    return Settings(
        mode="gateway",
        gateway_url="https://example.test",
        gateway_api_key="fixture",
        model="fixture",
    )


def test_validation_uses_isolated_database_and_restores_it(tmp_path, monkeypatch):
    original = tmp_path / "untouched.db"
    monkeypatch.setattr(db, "DB", original)
    results = check(settings(), ScriptedWorker())
    assert len(results) == 3
    assert all(r["passed"] for r in results)
    assert results[0]["activity_kind"] == "lesson"
    assert db.DB == original
    assert not original.exists()


def test_validation_restores_database_on_failure(tmp_path, monkeypatch):
    original = tmp_path / "untouched.db"
    monkeypatch.setattr(db, "DB", original)

    class BrokenWorker:
        def chat(self, messages):
            raise RuntimeError("private upstream details")

    with pytest.raises(RuntimeError):
        check(settings(), BrokenWorker())
    assert db.DB == original
    assert not original.exists()


def test_missing_key_reports_only_setting_name(monkeypatch, capsys):
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "")
    assert main() == 2
    assert "LLM_GATEWAY_API_KEY" in capsys.readouterr().out
