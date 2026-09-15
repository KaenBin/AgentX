"""Orchestrator agent: plan → delegate → synthesise.

The Orchestrator implements the orchestrator-workers pattern:

1. **Plan** — ask the Planner LLM to break the goal into steps.
2. **Delegate** — hand each step to a Worker, which may call tools.
3. **Synthesise** — combine step results into a final answer.

Hard limits (max steps / tool calls) come from configuration so autonomous runs
always terminate — an essential safety property for unattended SME automation.
"""

from __future__ import annotations

from agents.worker import Worker
from core.config import Settings, get_settings
from core.llm import LLMClient
from core.prompts import load_prompt
from core.state import AgentState, Plan, PlanStep, Role, StepStatus
from tools.base import ToolRegistry, build_default_registry
from utils.logging import get_logger

log = get_logger(__name__)


class Orchestrator:
    def __init__(
        self,
        llm: LLMClient,
        settings: Settings | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self._llm = llm
        self._settings = settings or get_settings()
        self._tools = tools or build_default_registry(self._settings)
        self._worker = Worker(llm=llm, tools=self._tools)
        self._planner_system = load_prompt("planner")
        self.max_steps = self._settings.max_agent_steps

    def run(self, goal: str) -> AgentState:
        """Execute the full plan-delegate-synthesise loop for a goal."""
        state = AgentState(goal=goal)
        state.add_message(Role.SYSTEM, self._planner_system)

        plan = self._make_plan(goal, state)
        state.plan = plan
        log.info("orchestrator.plan", extra={"steps": len(plan.steps), "goal": goal})

        while not plan.is_complete and state.step_count < self.max_steps:
            step = plan.next_pending()
            if step is None:
                break
            step.status = StepStatus.IN_PROGRESS
            state.step_count += 1
            try:
                result = self._worker.execute(step.description, state)
                step.result = result
                step.status = StepStatus.DONE
            except Exception as exc:  # noqa: BLE001 - one failing step shouldn't crash the run
                step.status = StepStatus.FAILED
                step.result = f"error: {exc}"
                log.warning("orchestrator.step.failed", extra={"step": step.id})

        state.finish(self._synthesise(state))
        return state

    def _make_plan(self, goal: str, state: AgentState) -> Plan:
        prompt = f"Goal: {goal}\n\nProduce the numbered plan."
        state.add_message(Role.USER, prompt)
        raw = self._llm.complete(state.messages)
        steps = self._parse_steps(raw)
        if not steps:
            # Degenerate but safe: treat the whole goal as one step.
            steps = [PlanStep(description=goal)]
        return Plan(goal=goal, steps=steps)

    @staticmethod
    def _parse_steps(raw: str) -> list[PlanStep]:
        steps: list[PlanStep] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Accept "1. text", "1) text", "- text".
            cleaned = line
            for prefix_char in (".", ")"):
                if cleaned[:2].rstrip(prefix_char).isdigit() or cleaned[0].isdigit():
                    parts = cleaned.split(prefix_char, 1)
                    if len(parts) == 2 and parts[0].strip().isdigit():
                        cleaned = parts[1].strip()
                        break
            if cleaned.startswith("- "):
                cleaned = cleaned[2:].strip()
            if cleaned:
                steps.append(PlanStep(description=cleaned))
        return steps

    def _synthesise(self, state: AgentState) -> str:
        if not state.plan:
            return "No plan was produced."
        results = [
            f"- {s.description}: {s.result}" for s in state.plan.steps if s.result is not None
        ]
        joined = "\n".join(results) if results else "(no step results)"
        prompt = (
            f"Goal: {state.goal}\n\n"
            f"Step results:\n{joined}\n\n"
            "Write the final answer for the user, concise and ready to use."
        )
        state.add_message(Role.USER, prompt)
        return self._llm.complete(state.messages)
