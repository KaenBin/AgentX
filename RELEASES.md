# AgentX Learn demo releases

These records describe reviewed source candidates. A record does not publish an
image, approve a merge, deploy a host or promote `dev` to production `master`.
The owner chooses the approved revision and records the actual deployment using
[DEMO-OPERATIONS.md](DEMO-OPERATIONS.md#record-an-update).

## 0.3.0 — demo operability candidate, 9 October 2026

Status: candidate awaiting PR review and owner merge. Human pilot results remain
uncollected. This release is for local fictional data and shared demo accounts.

Implementation revision: [49a004d](https://github.com/KaenBin/AgentX/commit/49a004d14e92e1dc58da2971cee175c861e756d7),
following readiness revision [61413b0](https://github.com/KaenBin/AgentX/commit/61413b0).
The version is defined in `src/core/version.py` and appears in `/ready` and API docs.
The final approved/deployed revision can include later review and documentation fixes;
record its full commit separately rather than deploying solely from this entry.

Changes:

- `/ready` reads the main SQLite database and checks the required core tables.
  Missing, corrupt, incomplete or locked databases return 503 without creating or
  seeding a database. The probe ignores browser rehearsal state and makes no model call.
- Docker health checks use `/ready`; `/health` keeps its prior liveness response.
- Every HTTP response carries a generated `X-Request-ID`. Unexpected errors before
  headers return a generic 500 with the same ID.
- Structured request logs record route templates and bounded metadata. They omit
  raw request data and exception text. Supported launchers disable raw access logs.
- The operator guide links diagnosis to existing backup, update and rollback steps.

Compatibility and recovery:

- Python 3.13 and the existing hashed dependency sets remain the supported setup.
  No dependency update or database schema change is introduced by this candidate.
- Existing authentication, learning evidence, deterministic scoring and procedure
  revisions retain their behavior. Unexpected 500 responses now have a JSON body;
  clients should continue checking HTTP status before reading a result.
- Readiness proves a read/schema check, not successful writes, database integrity,
  model availability or employee competence. Logs exclude detailed exception traces;
  reproduce faults in isolated fictional fixtures when more detail is needed.
- Back up before an update. Use the prior reviewed code and its matching backup for
  rollback as described in [DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md#updates-and-rollback).

Local validation on 9 October: 92 backend Python tests, four Chromium browser tests
and two Node dashboard tests passed; `pip check` found no dependency conflicts.
The Python run retains an existing Starlette/httpx deprecation warning. Container
smoke checks now cover readiness, request IDs and log redaction as well as recovery.
The local Docker engine did not respond to its version check, so container execution
requires the GitHub CI result before the owner treats this candidate as validated.

## 0.2.0 — prior demo foundation

The existing app declared version 0.2.0. The deployment foundation was merged to
`dev` in [PR #2](https://github.com/KaenBin/AgentX/pull/2), browser CI in
[PR #3](https://github.com/KaenBin/AgentX/pull/3), and the fictional pilot pack and
delivery plan in [PR #4](https://github.com/KaenBin/AgentX/pull/4).
This is source history, not evidence of a production deployment. The version's
shared accounts, SQLite storage, local binding and human-pilot limitations remain.
