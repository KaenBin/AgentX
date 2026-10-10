# AgentX Learn

A working local employee training app: web chat with source citations, a diagnostic, focused lessons, a separate scenario assessment, saved progress, and a trainer workspace for source approval and course publication.

The initial course uses a clearly fictional expense reimbursement policy. This app adapts the workflow from the sibling `agentx-training` prototype into the requested package structure and adds FastAPI, persistent chat, and the host's Ollama-compatible gateway connection.

## Start locally

Use Python 3.13, the version verified in CI. Run from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.txt
.\start.ps1
```

Open http://127.0.0.1:8010. The `/chat` URL also opens the web interface. API documentation is at `/docs`.

Demo accounts: `learner`, `alex`, and `trainer`. Password for each: `LearnDemo2026!`.

Use `./start.ps1 -Port 8011` if the default port is occupied. On Linux:

```sh
python3.13 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8010 --no-access-log
```

For a container demo with persistent storage and backup/restore, follow
[DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md). For the browser regression suite and
failure artifacts, see [BROWSER-TESTING.md](BROWSER-TESTING.md).
For readiness checks and request-ID diagnostics, see
[DEMO-OPERATIONS.md](DEMO-OPERATIONS.md); version and review references are in
[RELEASES.md](RELEASES.md).
For the automated previous-version upgrade, recovery and rollback exercise, see
[UPGRADE-REHEARSAL.md](UPGRADE-REHEARSAL.md).
Use the [demo release handover](DEMO-RELEASE-CHECKLIST.md) to select a reviewed
revision and record the actual installation, recovery and first human pilot.
For the CI source ZIP, checksum verification and local rebuild command, see
[SOURCE-BUNDLE.md](SOURCE-BUNDLE.md).
For a dated low-cost comparison before choosing remote hosting, see
[DEMO-HOSTING-OPTIONS.md](DEMO-HOSTING-OPTIONS.md).
For repeatable offline resource measurements and concurrent saved-result checks,
see [DEMO-CAPACITY.md](DEMO-CAPACITY.md).
For reviewed dependency updates and consistent hashed environments, see
[DEPENDENCY-MAINTENANCE.md](DEPENDENCY-MAINTENANCE.md).
For dated checks of known package advisories and their limits, see
[DEPENDENCY-ADVISORIES.md](DEPENDENCY-ADVISORIES.md).

## Try the complete journey

For a clean rehearsal, sign in as **trainer**, open **Progress**, and choose
**Start fresh live demo** or **Start fresh offline demo**. Each creates a new SQLite
database under `data/rehearsals` (or beside the configured database), seeds only the
original fictional policy, and opens as learner. A persistent banner labels the
workspace and mode. **Return to main workspace** restores the previous login.
Browser tabs share this selection. Rehearsal files are retained on exit; no existing
progress is reset or deleted. Live mode requires configured gateway credentials.

1. Sign in as `learner` and start the expense diagnostic. Deliberately miss the receipt question.
2. Submit answers. The result is scored and saved by the backend. Continue to your recommended lessons.
3. Open Ask your assistant. Ask “What should I do if my receipt is missing?” Expand its citation. Ask “What should I study next?” for a recommendation based on your saved attempt.
4. Ask “What is the capital of France?” to see an unsupported question referred to a trainer.
5. Complete the final assessment. Progress persists across reloads; `alex` has a separate history.
6. Sign in as `trainer`. Add a text or Markdown source, review its text and approve it. Create a draft, review the lesson and assessment JSON, then publish it.
7. Withdrawing source approval removes its courses from learner access. Published course versions and past attempts remain immutable history.

## Procedure readiness pilot

Trainers can open **Progress** for the results dashboard. It counts current
learner/course sessions by readiness state, lists critical gaps and open reviews,
and separates carried evidence from assigned and outstanding refreshers. Superseded
versions remain in expandable history and do not inflate current totals. Filters
affect the table; **View evidence** opens the saved objectives and decision records.
These counts do not measure time saved or represent employees with no recorded session.
Run dashboard aggregation checks with `node --test tests/dashboard.test.cjs`.

For a timed presentation and a separate fresh demo database, see [DEMO.md](DEMO.md).
The fictional learning path includes an expandable presenter walkthrough. Its
**Why this next step?** card preserves each new activity's selection mode, evidence
at selection, approved source reference and eventual outcome. The explanation uses
backend evidence, not private model reasoning, and survives reloads. Historical
activities without a recorded selection are not reconstructed.

The new **Expense procedure readiness — fictional pilot** course adds a persistent
coaching journey alongside the existing courses. Start it in Learning path:

1. Answer the diagnostic activities. Miss the receipt question to see focused coaching.
2. Select **Coach me through the next step**. In gateway mode, the model chooses from
   the backend's eligible activities. Demo mode uses a visibly labeled deterministic selection.
3. Review the missed step and answer a different scenario. Only fresh reassessment
   evidence demonstrates an objective; reading a lesson does not award a pass.
4. Inspect evidence by objective. The backend requires at least 80% of objectives
   demonstrated **and every critical objective**. With four pilot objectives, all four
   must be demonstrated. Diagnostic correctness alone never completes the course.
5. Ask a question using **Save review request**, then sign in as `trainer` and open
   Trainer studio to record guidance. Two failed fresh cases for an objective also
   create a review item. Guidance does not change scores or readiness.

Sessions resume after reload. The backend issues one activity at a time, keeps answer
keys and unissued cases out of learner responses, and rejects changed answers to
submitted activities. Duplicate submissions with the same answer return the saved
outcome without creating duplicate evidence. Withdrawing source approval blocks the
session. Existing quiz attempts remain historical practice and are not converted to
readiness evidence.

The database adds readiness tables on startup and preserves existing records. A new
fictional pilot course is added only when the canonical approved seed policy and
curated course are present. Custom courses require trainer-reviewed `readiness`
content before publication. Course generation does not automatically author this
schema yet. Back up the SQLite database before deploying any database change.

New endpoints: `POST /api/learning/start`, `GET /api/learning/{id}`, and
`POST /api/learning/{id}/next`, `/answer`, `/review`; trainers resolve requests through
`POST /api/learning/reviews/{id}/resolve`. The answer route takes an issued activity ID,
not a model-generated grade. Agent read tools now include `get_learning_state` and
`select_approved_activity`. Chat can recommend an activity; the learning-path action
authorizes issuing it. Model failures are explicit and do not silently switch modes.

Current limits: a newly approved course with unused cases is needed after cases are
exhausted. Exact prompt matching prevents previously issued readiness cases from
counting as fresh across courses; it does not detect semantic paraphrases or exposure
outside this app. Short-answer grading and learning-effectiveness evaluation remain
future work. Saved requests and trainer resolutions work locally; no email
notifications are sent. API tests use fake model workers, while the browser smoke
test uses offline mode; these do not establish live-model performance.

## Validate the live gateway

Set `LLM_GATEWAY_URL`, `LLM_GATEWAY_API_KEY` and `LLM_MODEL` in your local `.env`.
Keep the key out of source control and chat. Then run:

```powershell
.\.venv\Scripts\python.exe -m src.validate_live
```

This explicitly calls the configured model even when the app remains in demo mode.
It creates a temporary database containing only the fictional seed policy, establishes
a missed diagnostic step, and checks that the model selects an eligible activity
without changing the score. It also checks approved-source citations and referral
to a trainer for an unsupported question. It leaves the app database and mode unchanged.
The run makes at most twelve model requests and may incur gateway usage charges.

Exit code 0 means all smoke checks passed; 1 means validation failed; 2 means required
configuration is missing. Output excludes credentials and raw model responses.
These checks do not prove semantic citation accuracy, coaching quality, or learning
effectiveness. The activity explanation is the backend's approved reason for the
model's selection. Unsupported chat answers refer to a trainer; a saved review
request still requires the learner's explicit action or exhausted practice cases.

After a successful check, set `AGENT_MODE=gateway` and restart the app to test the
interactive experience. Fake-worker unit tests validate the check itself but do not
establish live-model performance.

Three consecutive live runs on 2026-09-26 passed all three checks after bounded
format recovery was added. Earlier runs failed intermittently; observed failures
included malformed structured output and timeouts. The adapter now
limits each response to 512 tokens and repeats the JSON contract after tool results.
Malformed JSON gets at most one format-repair attempt. The invalid response is never
executed, and repaired output must pass the same schema and eligibility checks.
Chat recovery consumes one of its five turns; activity selection permits at most two
model calls. Invalid tool names, arguments and citations still fail explicitly.
This is smoke-test evidence, not a reliability benchmark; invalid responses still
fail explicitly without issuing an invented activity or changing readiness scores.

## Procedure changes and targeted refreshers

Trainer studio now includes **Procedure updates**. For the fictional pilot:

1. Complete the readiness course as `learner`.
2. Sign in as `trainer`, open Trainer studio and select **Prepare fictional receipt
   policy update**. It adds a draft version allowing a written Finance exception when
   a supplier cannot replace a receipt. It does not publish anything yet.
3. Review the source diff, complete source, lessons and answer keys. The comparison
   marks receipt evidence for refresh. Unchanged objectives may retain demonstrated
   evidence only after the trainer approves that mapping.
4. Check the review confirmation and select **Approve version and assign refreshers**.
5. Sign in as `learner`. Three unchanged objectives retain explicitly labeled earlier
   evidence. The changed receipt objective requires an updated lesson and fresh case.
   Progress still contains the superseded version and its original attempts.

Custom revisions accept new source text and reviewed course JSON. Comparison is
deterministic: changed objective content, supporting source sections or completion
rules require refresh. This is conservative comparison, not model-generated semantic
impact analysis. The existing coach chooses eligible activities after activation.

Activation atomically approves the exact draft, retires the old source from retrieval,
records the trainer's mapping and creates successor sessions. Late submissions against
the old version are rejected. Duplicate activation does not duplicate assignments.
Generic source/course publication cannot bypass revision review. Stale drafts and
reused refresh questions are rejected. A changed or unmapped objective never inherits
a pass. Equivalent evidence retains a link to the prior session rather than being
recorded as a new attempt. Human content review remains necessary.

Endpoints: `POST /api/revisions/draft`, `/api/revisions/demo`, and
`/api/revisions/{id}/activate`. Revision drafts and answer keys are trainer-only.
The local prototype uses the existing trainer role; organization-level assignments
and production identity controls remain outside this milestone.

## Connect the host's gateway

Copy `.env.example` to `.env`, fill in your gateway details, and restart:

```dotenv
AGENT_MODE=gateway
LLM_GATEWAY_URL=https://your-host-gateway
LLM_GATEWAY_API_KEY=your-host-provided-key
LLM_MODEL=global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

The worker calls `POST /api/chat` with `X-API-Key`, exactly as the starter repository's Python examples do. The agent uses a bounded JSON tool-request protocol because some host gateway builds ignore native tool calling. It can retrieve sources, inspect the current learner's progress, and recommend a published lesson. It has no grading, approval, or write tools. Trainer actions and scoring are deterministic backend routes.

Gateway mode sends employee questions, a small amount of prior question context, and relevant approved passages to the configured model endpoint. Course generation sends the selected source. Credentials stay server-side. Missing configuration, invalid model output, provider failures, and invalid citations return explicit errors; they do not silently switch to demo mode.

Default `AGENT_MODE=demo` runs without a model or network calls. It returns matching source excerpts and deterministic recommendations, visibly labeled in the interface. Follow-up questions should be self-contained in demo mode. Live mode receives the last four questions as context and retrieves fresh evidence.

## Structure

```text
.github/workflows/       Automated tests
agents/system_prompts/  Coach instructions and JSON response protocol
agents/AGENTS.md         Coding constraints
src/main.py             FastAPI entry point, auth, web assets, API routes
src/core/config.py      Environment configuration and explicit modes
src/core/state.py       Agent state schema and user-specific snapshots
src/workflows/chain.py  Course drafting and validation
src/workflows/router.py Approval, publication, scoring and progress workflow
src/agents/             Bounded orchestrator and gateway worker
src/tools/              SQLite queries, local prompts and allowlisted tools
src/utils/              Logging helpers
src/web/                HTML, CSS and JavaScript frontend
tests/                  API, agent, gateway-adapter and workflow tests
data/                   Local SQLite database (ignored by Git)
```

## Run the agent directly

The browser and command line use the same training agent and account records:

```powershell
.\.venv\Scripts\python.exe -m src.agents --user learner
# Or ask one question:
.\.venv\Scripts\python.exe -m src.agents --user learner --question "What should I study next?"
```

Enter the account password when prompted; it is not accepted as a command-line argument. Type `/quit` to exit. The CLI prints the executed tools and citations, saves successful conversations, and closes its login session on exit.

In gateway mode, the model chooses the first tool and all subsequent steps. Its tools are `get_my_progress`, `retrieve_sources`, `get_course_outline`, `recommend_lesson`, `get_learning_state`, and `select_approved_activity`. The tool catalog is generated from typed schemas in `src/agents/protocol.py`; unknown actions, extra parameters, invalid IDs and mixed tool/answer responses are rejected. Tool argument/resource errors are returned to the model so it can correct its request within the five-turn budget. A final answer requires at least one successful tool call. Demo mode remains a deterministic, offline simulation.

## API and persistence

Sign in through `POST /api/login` with `name` and `password`; subsequent calls use the HttpOnly session cookie. `POST /chat` accepts `{"question":"What if my receipt is missing?"}` and returns `answer`, `sources`, `citations`, `out_of_scope`, and a tool trace. Chat history and attempts are private to each learner; trainers can view team assessment results.

`GET /api/state` returns approved courses, permitted source documents, attempts and recent chat. Mutation routes include `/api/document`, `/api/document/approve`, `/api/course/create`, `/api/course/publish`, and `/api/attempt`. `GET /health` reports app status and mode without credentials.

`TRAINING_DB` optionally sets a different database path. The default is `data/training.db`, resolved independently of the working directory. New source versions are new records; existing source text cannot be overwritten through the API.

## Tests

For a supervised 5–10 participant pilot, use [PILOT-TEST-PLAN.md](PILOT-TEST-PLAN.md)
and record observations in [PILOT-RESULTS-TEMPLATE.md](PILOT-RESULTS-TEMPLATE.md).
The plan separates app acceptance checks from independent learning assessment.
Participant copies: [form A](PILOT-ASSESSMENT-A.md), [form B](PILOT-ASSESSMENT-B.md),
and [procedure update](PILOT-ASSESSMENT-UPDATE.md). Keep the
[trainer scoring guide](PILOT-SCORING-GUIDE.md) separate from participant materials.
Use the [facilitator run sheet](PILOT-FACILITATOR-RUN-SHEET.md) for supervised sessions.
The [offline rehearsal report](PILOT-REHEARSAL-RESULTS.md) records backend preparation
evidence separately from participant results.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests run in demo mode with isolated databases; fake workers test live tool routing, limits, citations and errors without calling a provider. CI runs the same suite. On Windows hosts with a conflicting pytest temp-directory owner, pass `-p no:cacheprovider --basetemp=data/test-run-UNIQUE` using a new directory name. Pytest owns that test-only directory; do not point it at application data or an existing folder you want to preserve.

## Prototype boundaries

For the proposed path to a supported production product, see
[PRODUCT-DELIVERY-PLAN.md](PRODUCT-DELIVERY-PLAN.md) and the evidence-based
[production release checklist](PRODUCTION-RELEASE-CHECKLIST.md).

This is a local prototype with shared demo credentials. Before public use, replace them with managed identity, add login rate limits, organization/document access rules, HTTPS deployment, database migrations and backups. The frontend uses plain JavaScript and the database uses SQLite to keep local startup simple; React/Next.js, PostgreSQL, S3 and Bedrock Knowledge Bases from the proposal are not integrated yet.

Retrieval uses lexical overlap, not semantic search. It can miss paraphrases or match irrelevant passages. Citation IDs are checked against retrieved evidence, but that cannot prove each claim is supported. Evaluate answers with a trainer before using real company material. Generic course drafts have basic distractors and require review; the fictional readiness pilot and its receipt-policy update have curated separate scenario questions. Procedure comparison is deterministic and requires trainer approval; semantic change analysis, short-answer grading, and PDF/DOCX import are not implemented.

Implementation references: [FastAPI application lifespan](https://fastapi.tiangolo.com/advanced/events/) and [API testing](https://fastapi.tiangolo.com/tutorial/testing/).
