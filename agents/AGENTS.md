# AGENTS.md — Global rules for coding agents working on AgentX

This file defines the constraints, conventions, and commands any coding agent
(or human) must follow when contributing to this repository.

## Project intent
AgentX is a framework for building **practical agentic AI solutions for
Singapore SMEs**. Favour simple, reliable, well-tested patterns over clever ones.
Every feature should map to a real SME need (invoicing, quotes, customer comms,
lightweight reporting).

## Golden rules
1. **Deterministic first.** Reach for a `workflow` (chain/router) before an
   autonomous `agent` loop. Only use agents when the steps genuinely aren't
   known upfront.
2. **State is explicit.** Thread `core.state.AgentState` (and the typed models)
   through the system. Do not invent parallel, untyped state dicts.
3. **Tools are the only side effects.** All external actions go through a
   `tools.Tool`. File access is sandboxed; the database is read-only.
4. **Configuration is centralised.** Read settings via `core.config.get_settings()`,
   never from `os.environ` directly.
5. **No secrets in code or logs.** Use `.env` (see `.env.example`) and
   `utils.redact_secrets` when logging user-supplied text.

## Layout
- `src/core/` — entry points, config, LLM interface, explicit state schemas.
- `src/workflows/` — deterministic chains and routers.
- `src/agents/` — autonomous orchestrator + worker loops.
- `src/tools/` — sandboxed agent-computer interfaces.
- `src/utils/` — logging and plain helpers.
- `agents/system_prompts/` — role prompts (Planner, Worker, Evaluator).
- `tests/` — unit and integration tests.

## Commands
```bash
# Install (dev)
pip install -e ".[dev]"

# Lint & format
ruff check src tests
black --check src tests

# Type-check
mypy src

# Test
pytest                     # all
pytest -m "not integration"  # unit only
pytest --cov=. --cov-report=term-missing
```

## Conventions
- Python ≥ 3.10, type hints everywhere, Pydantic v2 for data models.
- Line length 100. Formatting via Black; linting via Ruff.
- Public functions/classes get short docstrings explaining *why*, not just *what*.
- New tools must define a Pydantic `args_schema` and validate inputs.
- Add/extend tests for every behavioural change. Do not weaken safety checks
  (sandbox path checks, read-only SQL guard) to make a test pass.

## Singapore SME defaults
- Currency: SGD, formatted `S$1,234.50` (`utils.format_sgd`).
- Timezone: `Asia/Singapore`.
- Be mindful of GST and PDPA when handling money and personal data.
