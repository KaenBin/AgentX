"""Explicit state management schemas.

Agentic systems are easiest to reason about, test, and debug when state is
*explicit* and *typed* rather than passed around as loose dicts. These Pydantic
models are the shared vocabulary used across workflows, agents, and tools.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Message(BaseModel):
    """A single turn in a conversation/transcript."""

    role: Role
    content: str
    name: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ToolCall(BaseModel):
    """A request to invoke a tool plus its (optional) recorded result."""

    id: str = Field(default_factory=_new_id)
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.result is not None


class PlanStep(BaseModel):
    """One unit of work in a plan produced by the orchestrator/planner."""

    id: str = Field(default_factory=_new_id)
    description: str
    status: StepStatus = StepStatus.PENDING
    result: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """An ordered set of steps toward a goal."""

    goal: str
    steps: list[PlanStep] = Field(default_factory=list)

    def next_pending(self) -> PlanStep | None:
        """Return the first step whose dependencies are all done."""
        done = {s.id for s in self.steps if s.status is StepStatus.DONE}
        for step in self.steps:
            if step.status is StepStatus.PENDING and all(d in done for d in step.depends_on):
                return step
        return None

    @property
    def is_complete(self) -> bool:
        return all(s.status in (StepStatus.DONE, StepStatus.SKIPPED) for s in self.steps) and bool(
            self.steps
        )


class AgentState(BaseModel):
    """The single source of truth threaded through an agent run.

    Passing one ``AgentState`` object (rather than many positional args) keeps
    orchestration code readable and makes runs trivially serialisable for
    logging, checkpointing, and replay.
    """

    session_id: str = Field(default_factory=_new_id)
    goal: str = ""
    plan: Plan | None = None
    messages: list[Message] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    scratchpad: dict[str, Any] = Field(default_factory=dict)
    step_count: int = 0
    finished: bool = False
    final_answer: str | None = None

    def add_message(self, role: Role, content: str, name: str | None = None) -> Message:
        message = Message(role=role, content=content, name=name)
        self.messages.append(message)
        return message

    def record_tool_call(self, call: ToolCall) -> None:
        self.tool_calls.append(call)

    def finish(self, answer: str) -> None:
        self.final_answer = answer
        self.finished = True
