# AgentX

**A practical framework for building agentic AI solutions for Singapore SMEs.**

AgentX gives small and medium enterprises a dependable foundation for automating
real work — invoicing reminders, quotation drafting, customer replies, and
lightweight reporting — using a mix of **deterministic workflows** and
**autonomous agents**, with safety and testability built in.

## Why AgentX

- **Deterministic-first.** Reach for a chain/router before an open-ended agent
  loop. Cheaper, faster, easier to test.
- **Explicit, typed state.** One `AgentState` object threads through the system —
  serialisable, debuggable, replayable.
- **Safe by construction.** File access is sandboxed; the database is read-only;
  autonomous loops have hard step/tool-call limits.
- **Provider-agnostic.** Swap OpenAI, Anthropic, or a local model without
  touching orchestration code. Ships with an offline mock so it runs with no key.
- **Singapore-aware.** SGD formatting, `Asia/Singapore` timezone, GST/PDPA-minded
  prompts.

## Project structure

```
app/
├── .github/workflows/       # CI/CD and automated test runners
├── agents/                  # Agent-specific definitions & system prompts
│   ├── system_prompts/      # Role prompts (Planner, Worker, Evaluator)
│   └── AGENTS.md            # Global rules, constraints, and commands for coding agents
├── src/
│   ├── core/                # Application entry points and configuration
│   │   ├── config.py
│   │   ├── state.py         # Explicit state management schemas
│   │   ├── llm.py           # Provider-agnostic LLM interface (+ mock)
│   │   ├── prompts.py       # Loads role system prompts
│   │   └── cli.py           # `agentx` command-line entry point
│   ├── workflows/           # Deterministic, multi-step orchestration (chains/routers)
│   │   ├── chain.py
│   │   └── router.py
│   ├── agents/              # Autonomous agent loops (Orchestrator-workers)
│   │   ├── orchestrator.py
│   │   └── worker.py
│   ├── tools/               # Agent-computer interfaces (ACI) & sandboxed actions
│   │   ├── base.py          # Tool + ToolRegistry abstraction
│   │   ├── file_ops.py
│   │   └── db_queries.py
│   └── utils/               # Plain helper functions and logging
└── tests/                   # Automated unit and integration tests
```

## Quickstart

```bash
# 1. Install (Python >= 3.10)
pip install -e ".[dev]"

# 2. Configure (the defaults use the offline mock provider — no key needed)
cp .env.example .env

# 3. Run the orchestrator against a goal
agentx run "Draft a reminder for outstanding invoices"

# 4. Inspect resolved config
agentx config
```

### Using a real LLM provider

Set these in `.env`:

```env
AGENTX_LLM_PROVIDER=openai        # or "anthropic"
AGENTX_LLM_API_KEY=sk-...
AGENTX_LLM_MODEL=gpt-4o-mini
```

Then install the matching extra: `pip install -e ".[openai]"` (or `.[anthropic]`).

## Choosing between workflows and agents

| Use a **workflow** when...                 | Use an **agent** when...                    |
| ------------------------------------------ | ------------------------------------------- |
| The steps are known ahead of time          | The steps depend on intermediate results    |
| You want maximum predictability & low cost | The task is open-ended                       |
| e.g. classify email → route to handler     | e.g. "research and draft a proposal"        |

- **Chain** (`workflows/chain.py`): a fixed pipeline; each step feeds the next.
- **Router** (`workflows/router.py`): predicate → handler dispatch.
- **Orchestrator + Worker** (`agents/`): plan a goal, delegate steps, synthesise.

## Extending: add a tool

Tools are the only way an agent affects the world. Subclass `Tool`, define a
Pydantic `args_schema`, and register it:

```python
from pydantic import BaseModel, Field
from tools.base import Tool, ToolRegistry

class SendEmailArgs(BaseModel):
    to: str = Field(description="Recipient address")
    body: str

class SendEmailTool(Tool):
    name = "send_email"
    description = "Send an email to a customer."
    args_schema = SendEmailArgs
    def run(self, to: str, body: str) -> str:
        ...  # integrate your provider here
        return f"sent to {to}"

registry = ToolRegistry([SendEmailTool()])
```

## Development

```bash
ruff check src tests      # lint
black src tests           # format
mypy src                  # type-check
pytest                    # all tests
pytest -m "not integration"   # unit only
```

See [`agents/AGENTS.md`](agents/AGENTS.md) for the full contributor/agent rulebook.

## License

MIT
