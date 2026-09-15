"""Command-line entry point for AgentX.

Usage:
    agentx run "Draft a GST-compliant invoice reminder for a late-paying client"
    agentx --help
"""

from __future__ import annotations

import argparse
import sys

from core.config import get_settings
from core.llm import build_llm_client
from utils.logging import configure_logging, get_logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentx", description="Agentic AI for Singapore SMEs.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the orchestrator agent against a goal.")
    run.add_argument("goal", help="The natural-language goal for the agent.")
    run.add_argument("--max-steps", type=int, default=None, help="Override max agent steps.")

    sub.add_parser("config", help="Print the resolved (non-secret) configuration.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings)
    log = get_logger(__name__)

    if args.command == "config":
        safe = settings.model_dump(exclude={"llm_api_key"})
        for key, value in safe.items():
            print(f"{key} = {value}")
        return 0

    if args.command == "run":
        # Imported here to avoid a circular import at module load.
        from agents.orchestrator import Orchestrator

        llm = build_llm_client(settings)
        orchestrator = Orchestrator(llm=llm, settings=settings)
        if args.max_steps:
            orchestrator.max_steps = args.max_steps
        state = orchestrator.run(args.goal)
        log.info("run.complete", extra={"session_id": state.session_id})
        print(state.final_answer or "(no answer produced)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
