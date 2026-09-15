"""Integration test: orchestrator plans, delegates to a worker, and synthesises.

Uses the offline MockLLMClient so the full loop runs deterministically with no
network access or API key.
"""

from __future__ import annotations

import pytest

from agents.orchestrator import Orchestrator
from core.state import StepStatus


@pytest.mark.integration
def test_orchestrator_end_to_end(settings, mock_llm, registry) -> None:
    orchestrator = Orchestrator(llm=mock_llm, settings=settings, tools=registry)
    state = orchestrator.run("Send reminders for outstanding invoices")

    assert state.finished
    assert state.final_answer is not None
    assert state.plan is not None
    # Mock planner returns a two-step plan; both should be executed.
    assert len(state.plan.steps) == 2
    assert all(s.status is StepStatus.DONE for s in state.plan.steps)
    # The run must respect the max-steps safety rail.
    assert state.step_count <= settings.max_agent_steps


@pytest.mark.integration
def test_worker_runs_db_tool(settings, mock_llm, registry) -> None:
    from agents.worker import Worker

    canned = (
        '```tool\n{"tool": "db_query", ' '"arguments": {"sql": "SELECT name FROM customers"}}\n```'
    )
    mock_llm._canned = {"current step": canned}  # type: ignore[attr-defined]

    worker = Worker(llm=mock_llm, tools=registry)
    from core.state import AgentState

    state = AgentState(goal="list customers")
    result = worker.execute("List all customers", state)

    assert "Ah Seng Trading" in result
    assert state.tool_calls and state.tool_calls[0].tool == "db_query"
