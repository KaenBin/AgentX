# Check locked dependencies for known advisories

Run this check before reviewing a dependency update and as part of monthly
maintenance. CI also runs it on pushes and PRs. It queries the PyPI advisory
service through [PyPA pip-audit](https://github.com/pypa/pip-audit), using the exact
names and versions in the current lockfiles. Reports record UTC timestamps and
the SHA-256 of each lock snapshot; advisories can change after a commit passes CI.

## Run locally

Use the hash-locked development environment and Python 3.13:

```powershell
./.venv/Scripts/python.exe -m pip install --require-hashes -r requirements.txt
./.venv/Scripts/python.exe audit_dependencies.py --output output/advisories/run-UNIQUE.json
```

On Linux use `.venv/bin/python`. Choose a new report filename each time; the
command refuses to overwrite existing evidence. It copies the three locks into
temporary storage, checks their exact pins/hashes and shared versions, and audits
the browser lock, which includes the full runtime and development package sets.
It does not resolve or install the packages being audited. The auditor itself and
its dependencies are installed from the development lock; they are absent from
the runtime container dependencies.

`--no-deps`, `--disable-pip` and `--require-hashes` keep the audit scoped to the
reviewed pins. The auditor contacts PyPI with public package names and versions;
it does not receive source content, gateway configuration, databases or pilot
records. Each run uses an empty temporary advisory cache rather than treating a
previous report as current evidence. The child has a 15-second socket timeout
and a five-minute overall timeout. Its `PIP_AUDIT_*` environment overrides are
removed so they cannot change the requested format, service or output destination.

## Interpret the report

| Outcome | Meaning | Command exit |
| --- | --- | --- |
| `passed` | Every expected package/version was audited, with no advisories returned by the selected service at that time | 0 |
| `findings` | Complete coverage with one or more known advisories | 1 |
| `error` | Invalid locks, unavailable service/tool, timeout, skipped packages, incomplete coverage, malformed response or inconsistent auditor exit | 1 |

An error is not a clean audit. Review its `reason` field. To diagnose tool/service
failures locally, run `python -m pip_audit --no-deps --disable-pip --require-hashes
-r requirements-browser.txt` from the same environment. Do not paste credentials
or private paths from diagnostics into PRs. Interrupted runs can leave incomplete
JSON; require a complete report with `outcome: passed` before relying on it.

Dependencies include `scopes`: `runtime`, `development` and/or `browser`. This
separates application packages from test tooling when assessing exposure. Findings
retain advisory IDs, aliases and suggested fixed versions. Free-form advisory
descriptions and subprocess diagnostics are excluded from the report. No finding
is suppressed and no automatic fix is applied.

When Git is available and the audit script plus all three locks are tracked there,
`source.commit` and `source.tracked_changes` identify the checkout. Extracted or
untracked bundles do not borrow an ancestor repository's Git identity; exact lock hashes remain
available. A dirty checkout is labeled and must not be described as the unchanged
commit's package set. Save the report, its checksum and final CI run with the
private release record when needed; `output/` is excluded from Git and bundles.
CI keeps the `dependency-advisories` artifact for 14 days, including handled audit
failures. An installation or runner failure before report creation leaves no
successful evidence and fails artifact upload.

## Triage and update

Check the advisory's affected versions, upstream explanation, application usage
and any proposed fix. An advisory match is a candidate for investigation; it does
not by itself prove an exploitable path in this app. A test-tool issue still needs
review even when the affected package is absent from the runtime image.

Use [dependency maintenance](DEPENDENCY-MAINTENANCE.md) to prepare a focused update
from `dev`, regenerate all locks, run compatibility/recovery checks, and request
review in a PR toward `dev`. Only the owner merges or promotes to `master`. Do not
use `--fix`, ignore IDs or bypass a failed check to make a PR pass. Resolve the
finding through a reviewed change, or leave it visible for the owner's decision.

This check is limited to known Python-package advisories supplied by PyPI. It does
not audit Python itself, container OS packages, GitHub Actions, browser binaries,
private packages, source-code vulnerabilities, exploitability or application
security controls. A passing report is dated evidence within that scope, not a
claim that the demo is vulnerability-free or production-ready.
