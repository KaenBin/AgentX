"""Autonomous agent loops (orchestrator-workers pattern).

The orchestrator decomposes a goal into a plan and delegates each step to a
worker. Workers use tools to act, and results flow back into shared state. This
pattern suits open-ended SME tasks where the exact steps are not known upfront.
"""

from agents.orchestrator import Orchestrator
from agents.worker import Worker

__all__ = ["Orchestrator", "Worker"]
