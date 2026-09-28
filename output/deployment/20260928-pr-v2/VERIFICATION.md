# Deployment artifact verification — 2026-09-28

Status: **PASS for local offline demonstration**. This is a source ZIP, not a
public deployment or proof of live course generation.

- Artifact: `AgentX_Learn_Deployment.zip`
- SHA-256: `d096b6f84054ca996dca746dbc60bfceb110c52dfbf7fa05855b35099737d1f0`
- Exact allowlist: 66 payload files plus `MANIFEST.sha256` (67 entries), including
  the tracked fictional `backup-demo.gif` used by the documented demo fallback.
- External checksum, ZIP CRC, every manifest hash, extracted-file hash and source
  working-tree bytes verified before tests.
- The extracted builder successfully verified the archive itself.
- Extracted source: **193 Python tests passed** (96.50 seconds), one existing
  Starlette/httpx deprecation warning; **2 Node dashboard tests passed**.
- Offline FastAPI TestClient: startup, `/health` (`mode=demo`), homepage, JavaScript,
  learner and trainer login, authenticated state and logout passed.
- `.env`, databases, credential files, caches, logs and virtual environments are
  absent. The packaged `.env.example` contains an empty API-key setting.
- Validation used `PYTHON_DOTENV_DISABLED=1`, `AGENT_MODE=demo`, cleared gateway
  environment variables and a new temporary database. No credentials file was
  opened and no model calls or external deployment were performed.

Source: `codex/openclaw-feature-readiness`, based on
`7eb6527eb8e884af4298e9a62e8c4e42c9dfe4f0` (`master`), with uncommitted feature
changes at packaging time. The final task report records the subsequent PR commit.

Runtime: existing project Python 3.12 virtual environment and existing Node runtime.
This did **not** test a fresh pip installation or a different computer. Dependency
ranges can resolve different versions. Detailed test logs and the machine-specific
verification JSON are retained locally; they are not included in the source ZIP.
To reproduce the code checks after extraction, run `python -m pytest -q` with
`PYTHON_DOTENV_DISABLED=1`, then `node --test tests/dashboard.test.cjs`.

Live limits remain as described in `OPENCLAW.md` and `DEMO-CHECKLIST.md`: the
Ollama-compatible gateway smoke checks were previously verified, but live course
generation timed out and real OpenClaw-server verification remains incomplete.
No API credential or private host/model value is included in this report.
