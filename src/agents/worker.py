"""Worker agent: executes a single plan step, optionally using a tool.

A Worker is deliberately narrow. It receives one step, decides whether a tool is
needed, acts, and returns a concise textual result. Keeping workers small makes
the overall system predictable and each action independently testable.
"""

from __future__ import annotations

import json
import re

from core.llm import LLMClient
from core.prompts import load_prompt
from core.state import AgentState, Role, ToolCall
from tools.base import ToolError, ToolRegistry
from utils.logging import get_logger

log = get_logger(__name__)

# The worker may emit a tool request as a fenced JSON block:
#   ```tool
#   {"tool": "db_query", "arguments": {"sql": "SELECT ..."}}
#   ```
_TOOL_BLOCK = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)


class Worker:
    def __init__(self, llm: LLMClient, tools: ToolRegistry) -> None:
        self._llm = llm
        self._tools = tools
        self._system = load_prompt("worker")

    def execute(self, step_description: str, state: AgentState) -> str:
        """Execute one step and return its result, recording tool use in state."""
        tool_catalogue = json.dumps(self._tools.specs(), default=str)
        prompt = (
            f"{self._system}\n\n"
            f"Overall goal: {state.goal}\n"
            f"Available tools: {tool_catalogue}\n\n"
            f"Current step: {step_description}\n\n"
            "If you need a tool, respond with a ```tool``` JSON block. "
            "Otherwise, respond with the plain-text result."
        )
        messages = [
            *state.messages,
            self._as_user(prompt),
        ]
        response = self._llm.complete(messages)

        tool_match = _TOOL_BLOCK.search(response)
        if tool_match:
            return self._run_tool(tool_match.group(1), state)

        state.add_message(Role.ASSISTANT, response)
        return response

    def _run_tool(self, raw_json: str, state: AgentState) -> str:
        try:
            request = json.loads(raw_json)
            name = request["tool"]
            arguments = request.get("arguments", {})
        except (json.JSONDecodeError, KeyError) as exc:
            return f"Could not parse tool request: {exc}"

        call = ToolCall(tool=name, arguments=arguments)
        try:
            call.result = self._tools.dispatch(name, arguments)
            log.debug("worker.tool.ok", extra={"tool": name})
            summary = f"Tool {name!r} returned: {json.dumps(call.result, default=str)}"
        except ToolError as exc:
            call.error = str(exc)
            log.warning("worker.tool.error", extra={"tool": name, "error": str(exc)})
            summary = f"Tool {name!r} failed: {exc}"

        state.record_tool_call(call)
        state.add_message(Role.TOOL, summary, name=name)
        return summary

    @staticmethod
    def _as_user(content: str):  # noqa: ANN205
        from core.state import Message

        return Message(role=Role.USER, content=content)
