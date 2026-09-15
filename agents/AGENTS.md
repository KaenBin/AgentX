# AGENTS.md — contributor & coding-agent rulebook

> Scaffold placeholder. Fill in as conventions are decided.

## Mission
Build practical agentic AI solutions for Singapore SMEs — deterministic-first,
safe by construction, provider-agnostic, and Singapore-aware.

## Ground rules (to be expanded)
- Prefer a workflow (chain/router) over an autonomous agent loop where possible.
- Tools are the only way an agent affects the world; keep them narrow and typed.
- Autonomous loops must have hard step/tool-call limits.
- File access is sandboxed; the database is read-only.

## Commands
```bash
ruff check src tests   # lint
black src tests        # format
mypy src               # type-check
pytest                 # tests
```
