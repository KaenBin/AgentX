"""Deterministic, multi-step orchestration primitives.

Not every problem needs an autonomous agent. Many SME use-cases are best served
by *deterministic* workflows — a fixed sequence of steps (a chain) or a
decision that routes input to the right handler (a router). These are cheaper,
faster, and far easier to test than open-ended agent loops.
"""

from workflows.chain import Chain, Step
from workflows.router import Route, Router

__all__ = ["Chain", "Step", "Router", "Route"]
