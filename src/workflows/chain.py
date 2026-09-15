"""Sequential chain: a deterministic pipeline of steps.

Each step is a callable that transforms the running context. Chains are ideal
for prompt-chaining patterns (e.g. extract → summarise → format) where the flow
is known ahead of time and each step's output feeds the next.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from utils.logging import get_logger

log = get_logger(__name__)

# A step receives the mutable context and returns a value stored under its name.
StepFn = Callable[[dict[str, Any]], Any]


@dataclass
class Step:
    name: str
    fn: StepFn


class Chain:
    """Run steps in order, threading a shared context dict through each one."""

    def __init__(self, steps: list[Step] | None = None) -> None:
        self._steps: list[Step] = list(steps or [])

    def add(self, name: str, fn: StepFn) -> Chain:
        """Append a step; returns self for fluent construction."""
        self._steps.append(Step(name=name, fn=fn))
        return self

    def run(self, initial: dict[str, Any] | None = None) -> dict[str, Any]:
        context: dict[str, Any] = dict(initial or {})
        for step in self._steps:
            log.debug("chain.step.start", extra={"step": step.name})
            result = step.fn(context)
            context[step.name] = result
            log.debug("chain.step.done", extra={"step": step.name})
        return context

    @property
    def step_names(self) -> list[str]:
        return [s.name for s in self._steps]
