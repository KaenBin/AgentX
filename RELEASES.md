# AgentX Learn demo releases

These records describe versioned source candidates and their review references. A record does not publish an
image, approve a merge, deploy a host or promote `dev` to production `master`.
The owner chooses the approved revision and records the actual deployment using
[DEMO-OPERATIONS.md](DEMO-OPERATIONS.md#record-an-update).

## 0.3.0 — demo operability candidate, 9 October 2026

Status: source merged into `dev` by the owner in
[PR #5](https://github.com/KaenBin/AgentX/pull/5) on 9 October 2026 at 09:29 Singapore.
Approved integration revision:
[`5fe0d50`](https://github.com/KaenBin/AgentX/commit/5fe0d50f434a701aec607a2b5bbbfb1444b6bd84).
Human pilot results remain
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

Local validation on 9 October: 95 backend Python tests, four Chromium browser tests
and two Node dashboard tests passed; `pip check` found no dependency conflicts.
The Python run retains an existing Starlette/httpx deprecation warning. Container
smoke checks now cover readiness, request IDs and log redaction as well as recovery.
The local Docker engine did not respond to its version check. Container execution
was subsequently verified by the passing PR CI, along with Windows, Linux and browser
checks ([reviewed revision CI](https://github.com/KaenBin/AgentX/actions/runs/37869680100)).
CodeRabbit's final review found no actionable issues; docstring coverage passed at 90%.
The rebuilt 92-entry source bundle passed integrity, Markdown-link and configured-key
exclusion checks; generated databases and private records remain excluded.

### Upgrade rehearsal follow-up

The owner merged [PR #6](https://github.com/KaenBin/AgentX/pull/6) into `dev` as
[`7cdd33c`](https://github.com/KaenBin/AgentX/commit/7cdd33cfaa0a353bed4fe891ada599b371653b61)
on 9 October 2026 at 13:39 Singapore. It adds [UPGRADE-REHEARSAL.md](UPGRADE-REHEARSAL.md) and an
`upgrade` CI job for the exact `0.2.0` baseline `8c5a357` to current demo revision.
It checks preserved evidence, a new answer, recovery and old-backup rollback.
The final implementation revision `54ede79` passed all five PR CI jobs in
[run 37873578484](https://github.com/KaenBin/AgentX/actions/runs/37873578484),
including the Docker upgrade rehearsal. This records automated fictional-data
evidence; the owner still records their installation and production promotion.

Local follow-up validation on 9 October: 109 backend tests passed after the source
identity guard was added; four Chromium tests and two Node tests also passed, and
dependency checks found no conflicts. The
95-entry source bundle passed integrity, local Markdown-link and key-exclusion checks.
The local Docker engine remains unresponsive. The first real Docker rehearsal passed
for source `bc64ee3` in [CI run 37870908669](https://github.com/KaenBin/AgentX/actions/runs/37870908669),
including upgrade, new writes, recovery and matching-backup rollback. The safe
`demo-upgrade-rehearsal` report was retained. Independent review then identified and
verified a guard against uncommitted Docker inputs. Use the final PR run linked
above when selecting a release, rather than attributing this earlier result to
later code.

### Keyboard and mobile follow-up

The owner merged [PR #7](https://github.com/KaenBin/AgentX/pull/7) into `dev` as
[`6e7222a`](https://github.com/KaenBin/AgentX/commit/6e7222ab88c1de7af7529f2bebf82f7f9ed2217b)
on 9 October 2026 at 15:26 Singapore. It improves view/activity focus, error and learning-update
announcements, secondary-copy and focus contrast, and navigation at 320 pixels.
See [ACCESSIBILITY-REVIEW.md](ACCESSIBILITY-REVIEW.md) for scope and human checks
still needed. It introduces no schema or dependency change and retains version
0.3.0; record the approved commit separately. All five integration CI jobs passed
in [run 37899064809](https://github.com/KaenBin/AgentX/actions/runs/37899064809).
Local validation passed 109 backend, 15 Chromium and two dashboard cases.
CodeRabbit confirmed the delayed-response fix and resolved its thread. UI function
documentation was added; its full coverage recheck remained rate-limited.
Use the [demo release handover](DEMO-RELEASE-CHECKLIST.md) for the outstanding
actual installation, recovery and human pilot records.

## 0.2.0 — prior demo foundation

The existing app declared version 0.2.0. The deployment foundation was merged to
`dev` in [PR #2](https://github.com/KaenBin/AgentX/pull/2), browser CI in
[PR #3](https://github.com/KaenBin/AgentX/pull/3), and the fictional pilot pack and
delivery plan in [PR #4](https://github.com/KaenBin/AgentX/pull/4).
This is source history, not evidence of a production deployment. The version's
shared accounts, SQLite storage, local binding and human-pilot limitations remain.
