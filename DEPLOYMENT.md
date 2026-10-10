# Deployment evidence: reproducible local artifact

This ZIP is a source deployment artifact for AgentX Learn, not evidence of public
cloud hosting. The organizer screenshot permits a URL or artifact; organizer
acceptance of a local artifact is not yet confirmed. No public endpoint is claimed.

## Reproduce from a clean folder (Windows)

Requirements: Python 3.13, package-install network access, and optional
Node.js for the dashboard tests. Extract the ZIP into a new folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.txt
$env:AGENT_MODE = 'demo'
.\start.ps1 -Port 8013
```

Open http://127.0.0.1:8013. GET /health must return status ok and mode demo.
Sign in with learner or trainer, password LearnDemo2026!. The app creates its local
SQLite database on startup and seeds fictional content. No existing learner records
or credentials are supplied in this archive.

For a fresh isolated rehearsal, sign in as trainer and use Progress -> Start fresh
offline demo. Verify that the original procedure is selected and the banner clearly
labels offline mode. The Return to main workspace button preserves both workspaces.

## Optional live mode

Copy .env.example to .env and supply your own authorized gateway URL, API key and
model. Set AGENT_MODE=gateway and restart. Never publish that file. Run
`.\.venv\Scripts\python.exe -m src.validate_live` for opt-in live checks; it uses
fictional data and can incur gateway charges. Offline operation requires no key.

## Verify the code

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/dashboard.test.cjs
```

Dependencies are pinned with hashes in requirements.txt (development) and
requirements-runtime.txt (runtime). See DEMO-DEPLOYMENT.md for the container
deployment, dependency update procedure, persistent data and backup instructions.

## Integrity and scope

Use [SOURCE-BUNDLE.md](SOURCE-BUNDLE.md) to select and retain a CI artifact,
verify the ZIP checksum before extraction, or rebuild from the selected source.

MANIFEST.sha256 lists every payload file and its SHA-256 digest, except the manifest
itself. The separate artifact checksum identifies the complete ZIP. The bundle uses
an explicit file allowlist: application source, system prompt, tests, CI workflow,
requirements, launch script and documentation. It excludes .env, databases, cookies,
logs, virtual environments, caches and local preview output.

The shared demo accounts, localhost binding and SQLite are prototype choices.
Managed authentication, tenant authorization and deployment hardening remain separate
work before public use. No email, repository push or external deployment is performed
by preparing this artifact.
