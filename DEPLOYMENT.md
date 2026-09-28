# Deployment evidence: reproducible local artifact

The deployment ZIP is a source artifact for AgentX Learn, not evidence of public
cloud hosting. The organizer screenshot permits a URL or artifact; organizer
acceptance of a local artifact is not yet confirmed. No public endpoint is claimed.

## Reproduce from a clean folder (Windows)

Requirements: Python 3.12 or newer, package-install network access, and optional
Node.js for the dashboard tests. Extract the ZIP into a new folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
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
Use `DEMO-CHECKLIST.md` for the presentation checks and disclosed live-mode limits.

## Optional live mode

Copy .env.example to .env and supply your own authorized gateway URL, API key and
model. Set AGENT_MODE=gateway and restart. Never publish that file. Run
`.\.venv\Scripts\python.exe -m src.validate_live` for opt-in live checks; it uses
fictional data and can incur gateway charges. Offline operation requires no key.
The default protocol remains Ollama-compatible. For an OpenClaw instance, follow
`OPENCLAW.md` and select `LLM_GATEWAY_PROTOCOL=openclaw` explicitly. Start with
`python -m src.check_gateway`, which sends no network or model requests.

## Verify the code

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:AGENT_MODE = 'demo'
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/dashboard.test.cjs
```

Archive extraction checks must be recorded separately from working-tree tests and
live rehearsals. An earlier bundle's verification report does not validate a newly
built ZIP. Dependencies are specified as compatible ranges, not
an exact lockfile. Installing them on a new machine can resolve newer versions.
Record whether package verification used an existing test runtime or a fresh
dependency installation; these are different reproduction checks.

## Build and verify a new artifact

After source and demonstration documentation are final, choose a new output folder:

```powershell
.\.venv\Scripts\python.exe build_deployment.py --output-dir output/deployment/demo-release-NEW
.\.venv\Scripts\python.exe build_deployment.py --verify output/deployment/demo-release-NEW/AgentX_Learn_Deployment.zip
Get-FileHash output/deployment/demo-release-NEW/AgentX_Learn_Deployment.zip -Algorithm SHA256
```

Compare the complete ZIP hash with `AgentX_Learn_Deployment.sha256` in the same
folder. The builder and verifier also check the exact entry list, ZIP integrity,
and every payload's SHA-256 against the embedded manifest. Then extract into a new
folder and perform the startup, login and test checks above. Do not extract over an
existing workspace or learner database.

The builder refuses to replace an existing ZIP or checksum; use a new folder for
each candidate. Missing required source, tests or documents fail the build before
artifacts are written. File and directory links are rejected. With identical input
bytes and the same Python/compression runtime, sorted entries, fixed timestamps
and fixed permissions produce identical archive bytes regardless of source mtimes.

## Integrity and scope

MANIFEST.sha256 lists every payload file and its SHA-256 digest, except the manifest
itself. The separate artifact checksum identifies the complete ZIP. The bundle uses
an exact file allowlist maintained in `build_deployment.py`: application source,
system prompt, tests, CI workflow, requirements, launch script and documentation.
It includes the OpenClaw adapter documentation, configuration check, gateway tests,
demo checklist and the builder itself. The tracked, fictional `backup-demo.gif`
is included so the documented application-failure fallback also works from the
extracted bundle. New runtime/test files must be added to the allowlist;
packaging tests flag omissions. It excludes .env, databases, cookies,
logs, virtual environments, caches and local preview output.

Building does not load `.env` or call any model. `.env.example` must contain an
empty API-key value. If `LLM_GATEWAY_API_KEY` is already supplied in the builder's
process environment, its bytes are additionally checked against every payload and
never printed. This optional check does not load credentials from files or replace
reviewing the allowlisted source and documentation for accidentally copied secrets.

The shared demo accounts, localhost binding and SQLite are prototype choices.
Managed authentication, tenant authorization and deployment hardening remain separate
work before public use. No email, repository push or external deployment is performed
by preparing this artifact.
