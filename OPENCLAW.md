# OpenClaw integration and feature checks

## What needs configuring

AgentX Learn already implements approved-source retrieval, learner progress,
diagnostics, deterministic grading, readiness activities, trainer review, and
course publication in its own backend. Its original model adapter uses the
organizer's Ollama-compatible gateway (`/api/chat` with `X-API-Key`). That route
does not require OpenClaw. Merely changing its URL to an OpenClaw host will fail.

The optional `openclaw` protocol added here calls `/v1/chat/completions` with a
Gateway bearer token. It supports all three existing model entry points:

| Feature | OpenClaw output | Application remains responsible for |
| --- | --- | --- |
| Ask your assistant | One JSON read-tool request or final answer | Tool allowlist, approved-source retrieval, citations, per-user history |
| Coach me through the next step | An eligible activity ID | Ownership, fresh-case eligibility, issuing the activity, deterministic scoring |
| Trainer course drafting | Course JSON | Source approval, schema/source-section validation, saving a draft, explicit trainer publication |

No OpenClaw plugin or skill is needed for these application tools. They remain
local to this application and are not exposed as remote OpenClaw tools. The
adapter does not add grading, publication, chat sending or deployment tools.

## Configure the actual OpenClaw server

These instructions were checked against the official documentation on 2026-09-27.
First check the installed OpenClaw version and its configuration schema. The
current docs use `agents.entries`; older installations may differ. Have the server
owner merge the appropriate settings into the existing configuration, keeping
other agents and authentication intact. Do not replace a shared server's config.

Required changes, using a dedicated agent named `agentx-training` as an example:

```json
{
  "gateway": {
    "auth": { "mode": "token" },
    "http": {
      "endpoints": {
        "chatCompletions": { "enabled": true }
      }
    }
  },
  "agents": {
    "entries": {
      "agentx-training": {
        "workspace": "/path/to/dedicated-clean-workspace",
        "model": "configured-provider/actual-model",
        "skills": [],
        "tools": {
          "deny": ["*"],
          "elevated": { "enabled": false }
        }
      }
    }
  }
}
```

This is a merge example with placeholders, not a complete deployable config.
Use an existing authorized Gateway token or have the server owner configure one
securely; no token belongs in this document. Keep the endpoint private (for
example, an authorized SSH tunnel to its loopback port) or behind appropriate
HTTPS access controls. Do not publicly expose the Gateway just to run this app.

OpenClaw runs an agent turn, not a plain model proxy. Its server-side tools must
be denied on the dedicated agent: the application's local tool whitelist cannot
prevent remote OpenClaw side effects. `tool_choice: none` and an empty `allow`
list are not substitutes for that configuration. The Gateway token is powerful;
keep it only in the backend. The adapter never forwards client-supplied routing
headers, native tools, `user`, or a persistent session header.

Authenticated requests do not follow HTTP redirects, including redirects on the
same host. Configure the final base URL directly so a redirect cannot forward
the Gateway token or organizer API key to another destination.

Each call therefore starts a new OpenClaw session using the application's supplied
messages. This prevents accidental shared conversation history across learners;
it does not mean the remote server stores nothing. OpenClaw can persist sessions
and inject its own workspace/system context. Use a clean dedicated workspace and
verify the full JSON interaction on the actual installed version.

## Configure this application locally

Create an ignored `.env` from `.env.example`, then supply the real values:

```dotenv
AGENT_MODE=demo
LLM_GATEWAY_PROTOCOL=openclaw
LLM_GATEWAY_URL=http://127.0.0.1:18789
LLM_GATEWAY_API_KEY=<authorized-gateway-token>
LLM_MODEL=openclaw/agentx-training
```

The URL is the base URL, without `/v1` or `/v1/chat/completions`. The key is the
**OpenClaw Gateway token**, not the organizer's `X-API-Key`. `LLM_MODEL` selects
the dedicated OpenClaw agent; configure its actual provider/model on the server.
Keep `LLM_GATEWAY_PROTOCOL=ollama` to continue using the existing host gateway.
The app mode is still `demo` or `gateway`, independently of the selected protocol.

First run the configuration check. It makes zero network/model requests and
prints setting names and status, not the token or host address:

```powershell
.\.venv\Scripts\python.exe -m src.check_gateway
```

Exit 0 means the local settings are present and structurally valid, **not** that
OpenClaw is reachable, authorized, safely configured, or returning usable output.
Exit 2 lists missing or invalid settings. Offline mode still works without keys.

## Verify before using the live service

After the server owner confirms the dedicated agent configuration and usage is
authorized, run the existing opt-in live smoke check:

```powershell
.\.venv\Scripts\python.exe -m src.validate_live
```

This uses a disposable database with fictional data and calls the configured model
even if the application remains in demo mode. It can incur model charges. It
checks activity eligibility without changing scores, approved-source citations,
and referral for an unsupported question. It does not validate server-side tool
policy, semantic answer quality, or course generation. To test course generation,
use a fresh **live** rehearsal as trainer, approve a fictional source, generate a
draft, and inspect its lessons/questions and source sections before publishing.

Only after these checks pass, set `AGENT_MODE=gateway` and restart the local app.
Use the existing demo/readiness/revision walkthrough to verify the interactive
journey. Errors remain explicit; the app does not silently switch to offline mode.

Chat and activity selection request up to 512 output tokens per call. Course
drafting requests up to 4096 because a complete lesson/question bank needs more
space. Chat and activity calls use a 60-second network timeout; course drafting
uses 180 seconds to accommodate longer responses. A timeout fails the request
without an automatic retry. The server may still process or bill a timed-out
request, so investigate before explicitly retrying.
OpenClaw describes token limits and sampling as best-effort provider
options, so these are requested budgets, not universal server-side guarantees.
Malformed, empty, native-tool, or unusable responses fail closed; the existing
bounded JSON repair and local validation still apply. Remote messages themselves
are never executed as code.

## Offline regression checks and evidence limits

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/dashboard.test.cjs
```

Transport tests verify Ollama compatibility and the OpenClaw wire contract.
Feature tests use a loopback HTTP fixture and isolated fictional databases for
the real adapter and application workflows. They do not contact a real OpenClaw
instance and must not be reported as live-model validation. No production token,
environment file, shared server configuration, or deployment is supplied by Git.

## Official references

- [Chat Completions HTTP API and authentication](https://docs.openclaw.ai/gateway/openai-http-api)
- [Agent entries and multi-agent configuration](https://docs.openclaw.ai/gateway/config-agents/entries-and-multi-agent)
- [Tool policy](https://docs.openclaw.ai/gateway/config-tools/tool-policy)
- [Tool policy matching](https://docs.openclaw.ai/plugins/sdk-entrypoints/tool-policy-and-sandbox)
- [System prompt and workspace context](https://docs.openclaw.ai/concepts/system-prompt)
- [Session persistence](https://docs.openclaw.ai/reference/session-management-compaction/store)
