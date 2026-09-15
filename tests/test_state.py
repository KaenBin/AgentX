"""Unit tests for core.state schemas."""

from __future__ import annotations

from core.state import AgentState, Plan, PlanStep, Role, StepStatus, ToolCall


def test_plan_next_pending_respects_dependencies() -> None:
    a = PlanStep(description="a")
    b = PlanStep(description="b", depends_on=[a.id])
    plan = Plan(goal="g", steps=[a, b])

    # b is blocked until a is done.
    assert plan.next_pending() is a
    a.status = StepStatus.DONE
    assert plan.next_pending() is b


def test_plan_completeness() -> None:
    step = PlanStep(description="only")
    plan = Plan(goal="g", steps=[step])
    assert not plan.is_complete
    step.status = StepStatus.DONE
    assert plan.is_complete


def test_empty_plan_is_not_complete() -> None:
    assert not Plan(goal="g").is_complete


def test_agent_state_helpers() -> None:
    state = AgentState(goal="do a thing")
    state.add_message(Role.USER, "hi")
    assert state.messages[-1].content == "hi"

    call = ToolCall(tool="read_file", arguments={"path": "x"}, result="ok")
    state.record_tool_call(call)
    assert call.succeeded
    assert state.tool_calls[0].tool == "read_file"

    state.finish("done")
    assert state.finished and state.final_answer == "done"


def test_tool_call_error_is_not_success() -> None:
    call = ToolCall(tool="db_query", error="boom")
    assert not call.succeeded
