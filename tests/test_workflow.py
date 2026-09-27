import json
import pytest
from src.agents.orchestrator import TrainingOrchestrator
from src.agents.worker import GatewayWorker, GatewayError
from src.core.config import Settings
from src.core.state import snapshot
from src.tools import db_queries as db
from src.tools.training_tools import execute
from src.workflows.router import act


@pytest.fixture
def users(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    db.init()
    return {
        name: db.user(db.login(name, "LearnDemo2026!"))
        for name in ["learner", "alex", "trainer"]
    }


class FakeWorker:
    def __init__(self, *results):
        self.results = iter(results)
        self.messages = []

    def chat(self, messages):
        self.messages.append(list(messages))
        return json.dumps(next(self.results))


def live(worker):
    return TrainingOrchestrator(
        Settings(
            mode="gateway",
            gateway_url="https://example.test",
            gateway_api_key="test",
            model="test",
        ),
        worker,
    )


class TextWorker:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def chat(self, messages):
        self.calls += 1
        return next(self.responses)


def test_malformed_json_gets_one_repair_before_any_tool_executes(users):
    worker = TextWorker(
        'Here is the result: {"tool":"get_my_progress","args":{}}',
        '{"tool":"get_my_progress","args":{}}',
        '{"answer":"Start your learning path."}',
    )
    result = live(worker).run(users["learner"], "What should I study next?")
    assert result["trace"] == ["get_my_progress"]
    assert worker.calls == 3


def test_repeated_malformed_json_fails_without_saving_chat(users):
    worker = TextWorker("not json", "still not json")
    with pytest.raises(GatewayError, match="invalid structured"):
        live(worker).run(users["learner"], "What should I study next?")
    assert worker.calls == 2
    assert snapshot(users["learner"])["chats"] == []


def test_format_repair_does_not_expand_five_turn_limit(users):
    tool = '{"tool":"get_my_progress","args":{}}'
    worker = TextWorker(tool, tool, tool, tool, "not json")
    with pytest.raises(GatewayError, match="invalid structured"):
        live(worker).run(users["learner"], "What should I study next?")
    assert worker.calls == 5
    assert snapshot(users["learner"])["chats"] == []


def test_grounded_chat_persists_privately(users):
    result = TrainingOrchestrator().run(
        users["learner"], "What if my receipt is missing?"
    )
    assert "duplicate" in result["answer"]
    assert result["sources"][0]["section"] == 1
    assert len(snapshot(users["learner"])["chats"]) == 1
    assert snapshot(users["alex"])["chats"] == []


def test_out_of_scope_abstains(users):
    result = TrainingOrchestrator().run(
        users["learner"], "What is the capital of France?"
    )
    assert result["out_of_scope"]
    assert result["sources"] == []


def test_progress_recommends_actual_gap(users):
    act(
        users["learner"],
        "/api/attempt",
        {"course_id": 1, "phase": "diagnostic", "answers": [1, 0, 1, 1]},
    )
    result = TrainingOrchestrator().run(users["learner"], "What should I study next?")
    assert result["trace"] == ["get_my_progress", "recommend_lesson"]
    assert "Receipt evidence" in result["answer"]


def test_model_loop_and_citation_validation(users):
    worker = FakeWorker(
        {"tool": "retrieve_sources", "args": {"query": "missing receipt"}},
        {"tool": "retrieve_sources", "args": {"query": "manager approval"}},
        {"answer": "Request a duplicate receipt. [1]"},
    )
    result = live(worker).run(users["learner"], "What if my receipt is missing?")
    assert len(worker.messages) == 3
    assert any(s["section"] == 3 for s in result["sources"])
    assert result["sources"][0]["citation"] == 1
    assert len({(s["document_id"], s["section"]) for s in result["sources"]}) == len(
        result["sources"]
    )


@pytest.mark.parametrize("answer", ["Unsupported claim [99]", "No citation"])
def test_invalid_citations_do_not_save(users, answer):
    with pytest.raises(GatewayError):
        live(
            FakeWorker(
                {"tool": "retrieve_sources", "args": {"query": "missing receipt"}},
                {"answer": answer},
            )
        ).run(users["learner"], "missing receipt")
    assert snapshot(users["learner"])["chats"] == []


def test_tools_cannot_impersonate_or_publish(users):
    with pytest.raises(ValueError):
        execute(users["learner"], "get_my_progress", {"user_id": users["alex"]["id"]})
    with pytest.raises(ValueError):
        execute(users["learner"], "publish_course", {})


def test_loop_limit(users):
    with pytest.raises(GatewayError, match="five-step"):
        live(FakeWorker(*[{"tool": "get_my_progress", "args": {}}] * 5)).run(
            users["learner"], "progress"
        )
    assert snapshot(users["learner"])["chats"] == []


def test_revocation_during_model_response(users):
    class Withdraw:
        def chat(self, messages):
            if len(messages) == 2:
                return json.dumps(
                    {"tool": "retrieve_sources", "args": {"query": "missing receipt"}}
                )
            act(users["trainer"], "/api/document/approve", {"id": 1, "approved": False})
            return json.dumps({"answer": "Request a duplicate. [1]"})

    with pytest.raises(ValueError, match="withdrawn"):
        live(Withdraw()).run(users["learner"], "missing receipt")


def test_gateway_configuration_fails_explicitly():
    with pytest.raises(ValueError):
        Settings(
            mode="gateway", gateway_url="", gateway_api_key="", model=""
        ).validate()


def test_gateway_transport_and_redacted_failure(monkeypatch):
    settings = Settings(
        mode="gateway",
        gateway_url="https://example.test",
        gateway_api_key="secret-key",
        model="sonnet",
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"message":{"content":"hello"}}'

    def transport(request, timeout):
        assert request.full_url == "https://example.test/api/chat"
        assert request.get_header("X-api-key") == "secret-key"
        assert json.loads(request.data)["stream"] is False
        assert json.loads(request.data)["options"]["num_predict"] == 512
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", transport)
    assert GatewayWorker(settings).chat([]) == "hello"

    def broken(*args, **kwargs):
        raise RuntimeError("secret-key")

    monkeypatch.setattr("urllib.request.urlopen", broken)
    with pytest.raises(GatewayError) as exc:
        GatewayWorker(settings).chat([])
    assert "secret-key" not in str(exc.value)


def test_agent_selects_tools_from_first_turn(users):
    worker = FakeWorker(
        {"tool": "get_my_progress", "args": {}},
        {"tool": "get_course_outline", "args": {"course_id": 1}},
        {"tool": "recommend_lesson", "args": {"course_id": 1, "skill": 0}},
        {"answer": "Start with receipt evidence. [1]"},
    )
    result = live(worker).run(users["learner"], "Help me understand expense claims")
    assert result["trace"] == [
        "get_my_progress",
        "get_course_outline",
        "recommend_lesson",
    ]
    context = json.loads(worker.messages[0][1]["content"])
    assert "initial_tool_result" not in context
    assert {tool["name"] for tool in context["available_tools"]} == {
        "get_my_progress",
        "retrieve_sources",
        "get_course_outline",
        "recommend_lesson",
        "get_learning_state",
        "select_approved_activity",
    }


def test_tool_error_can_be_corrected(users):
    worker = FakeWorker(
        {"tool": "recommend_lesson", "args": {"course_id": True, "skill": 0}},
        {"tool": "recommend_lesson", "args": {"course_id": 1, "skill": 0}},
        {"answer": "Request an itemized receipt. [1]"},
    )
    result = live(worker).run(users["learner"], "Help with receipts")
    assert result["trace"] == ["recommend_lesson"]
    assert "error" in json.loads(worker.messages[1][-1]["content"])["tool_result"]


def test_course_outline_has_no_answer_keys(users):
    outline = execute(users["learner"], "get_course_outline", {"course_id": 1})
    assert set(outline["lessons"][0]) == {"skill", "title"}
    act(users["trainer"], "/api/document/approve", {"id": 1, "approved": False})
    with pytest.raises(ValueError):
        execute(users["learner"], "get_course_outline", {"course_id": 1})


def test_no_tool_final_answer_rejected(users):
    with pytest.raises(GatewayError, match="consult a tool"):
        live(FakeWorker({"answer": "You passed the course."})).run(
            users["learner"], "How did I do?"
        )


def test_unknown_tool_and_mixed_decision_rejected(users):
    for decision in [
        {"tool": "publish_course", "args": {}},
        {"tool": "get_my_progress", "args": {}, "answer": "done"},
    ]:
        with pytest.raises(GatewayError):
            live(FakeWorker(decision)).run(users["learner"], "Publish my course")
    assert snapshot(users["learner"])["chats"] == []


def test_fabricated_citation_without_sources_rejected(users):
    with pytest.raises(GatewayError, match="citations"):
        live(
            FakeWorker(
                {"tool": "get_my_progress", "args": {}},
                {"answer": "Your progress [1]"},
            )
        ).run(users["learner"], "progress")
