# AgentX

**A scaffold for building practical agentic AI solutions for Singapore SMEs.**

This branch is an **initial commit — structure only, no implementation yet.**
It lays out a clean, opinionated skeleton so features can be added deliberately.
Every module is a documented placeholder describing its intended responsibility.

## Design principles (the shape we're building toward)

- **Deterministic-first.** Prefer a chain/router over an open-ended agent loop.
- **Explicit, typed state.** One `AgentState` threads through the system.
- **Safe by construction.** Sandboxed file access, read-only DB, hard limits on
  autonomous loops.
- **Provider-agnostic.** Swap OpenAI / Anthropic / local models freely; an
  offline mock lets it run with no key.
- **Singapore-aware.** SGD, `Asia/Singapore` timezone, GST/PDPA-minded prompts.

## Project structure

```
.
├── .github/workflows/       # CI (lint, format, type-check, test)
├── agents/
│   ├── system_prompts/      # Role prompts: planner, worker, evaluator
│   └── AGENTS.md            # Contributor & coding-agent rulebook
├── src/
│   ├── core/                # config, state, llm, prompts, cli
│   ├── workflows/           # deterministic orchestration: chain, router
│   ├── agents/              # autonomous loops: orchestrator, worker
│   ├── tools/               # agent-computer interfaces: base, file_ops, db_queries
│   └── utils/               # helpers, logging
└── tests/                   # unit & integration tests
```

## Status

Nothing is implemented. Modules raise `NotImplementedError` or contain only
docstrings. See [`agents/AGENTS.md`](agents/AGENTS.md) for the intended rules.

## Development

```bash
pip install -e ".[dev]"
ruff check src tests   # lint
black src tests        # format
mypy src               # type-check
pytest                 # tests
```

## License

MIT
