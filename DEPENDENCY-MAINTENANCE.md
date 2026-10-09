# Maintain the demo dependencies

Review dependency updates monthly, and sooner when an applicable vulnerability or
compatibility issue is reported. The owner decides urgency and merges reviewed PRs.
This procedure is manual; it does not enable scheduled jobs, automatic merges or
changes to the running demo.

## Lock ownership

| Input | Generated lock | Purpose |
| --- | --- | --- |
| `requirements-runtime.in` | `requirements-runtime.txt` | Application/container dependencies |
| `requirements-dev.in` | `requirements.txt` | Runtime plus backend tests and capacity tooling |
| `requirements-browser.in` | `requirements-browser.txt` | Development environment plus browser testing |

Resolve runtime first, then constrain development to runtime, then browser to
development. `lock_dependencies.py --check` validates that every package has an
exact version and SHA-256 hashes and that parent packages retain the same versions
in child locks. CI runs this check on both Windows and Linux. It checks the lock
format and shared pins; the locked installations and test jobs establish whether
the dependencies actually install and work.

The checker deliberately accepts only the current plain `name==version` plus
hashes format. URLs, index directives, extras and environment markers require a
reviewed change to the checker and platform validation before introducing them.
Hashes verify downloaded content against the reviewed lock; they do not establish
that a dependency is safe. See [pip hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/).

## Prepare an update

Start from current `dev` with a clean tracked tree. Create a branch such as
`chore/dependencies-YYYY-MM`; preserve private databases, configuration and pilot
records. Use Python 3.13, matching CI. Run the compiler in a separate maintenance
virtual environment so its build tools do not affect the app environment:

```powershell
python -m venv tmp/lock-tools
./tmp/lock-tools/Scripts/python.exe -m pip install pip-tools==7.6.2
./tmp/lock-tools/Scripts/python.exe lock_dependencies.py --check
```

Compiler version 7.6.2 was exercised on 9 October 2026. This bootstrap installation
is a maintenance tool installation, not a hash-locked app dependency. Review its
version separately before changing it. Keep it out of the runtime lock/image.
On Linux use `python3.13` and `tmp/lock-tools/bin/python`.

Choose one operation:

```powershell
# Rebuild annotations/hashes while preferring the existing versions:
./tmp/lock-tools/Scripts/python.exe lock_dependencies.py --refresh

# Update one existing package, within the bounds declared in the inputs:
./tmp/lock-tools/Scripts/python.exe lock_dependencies.py --package fastapi

# Update all packages within those bounds for a monthly review:
./tmp/lock-tools/Scripts/python.exe lock_dependencies.py --upgrade
```

Repeat `--package` for several existing packages. Names are normalized; version
expressions and unknown names are rejected. To add a package or change allowed
versions, edit its input first, then refresh. The resolver can change related
dependencies when needed; review the entire resulting diff. `--refresh` prefers
existing pins but does not guarantee zero version changes after an input change.
The behavior follows [pip-tools updates and layered requirements](https://pip-tools.readthedocs.io/en/stable/).

The tool compiles in temporary storage beneath the checkout, preserving current
locks until all three candidates validate. A compiler timeout, failure or invalid
candidate leaves original lockfiles intact. It detects concurrent input/lock edits before
applying the candidate. A handled write failure attempts to restore the original
bytes. This is not a filesystem transaction: a process kill, power loss or failed
rollback can leave partial files. Inspect `git diff` and restore only the affected
lockfiles from the known starting revision before retrying. Do not run two updates
or edit inputs/locks while resolution is running.

## Validate and request review

1. Review all input and lock diffs, upstream release notes and applicable advisories.
   Record the reason, old/new versions, compatibility concerns and compiler version
   in the PR. Review removed packages and changed hashes as well as new versions.
2. Install `requirements.txt` with `--require-hashes` into a fresh Python 3.13
   environment; run `pip check`, `lock_dependencies.py --check`, the full backend
   suite and `node --test tests/dashboard.test.cjs` (Node 22).
3. Install `requirements-browser.txt` in a separate fresh environment and run the
   Chromium suite using [BROWSER-TESTING.md](BROWSER-TESTING.md). Recheck live gateway
   behavior separately if the affected package changes it; offline/fake-model tests
   do not establish live provider compatibility.
4. Rebuild the source bundle with `build_deployment.py` and check its manifest and
   configured-key exclusion. Use the container, upgrade and benchmark CI jobs as
   well as the Windows/Linux tests. Dependency resolution on one OS does not prove
   support on another. Require all applicable jobs to pass on the final PR commit.
5. Commit input and lock changes together, push the feature branch, open a PR
   **toward `dev`**, and request CodeRabbit review. Keep failures and unresolved
   findings visible. Only the owner merges and promotes `dev` to production `master`.

Do not relax hash checking or bypass failing jobs to make an update pass. If an
update is unsuitable, correct it or close the PR. Vulnerability assessment is a
separate review; this tool does not scan advisories or claim no vulnerabilities.

## Install and recover

A merged dependency PR does not update a running installation. The owner selects a
reviewed revision and records its CI evidence using the
[release handover](DEMO-RELEASE-CHECKLIST.md). Preserve the previous source/image and
its matching stopped-app backup. Follow [DEMO-OPERATIONS.md](DEMO-OPERATIONS.md) and
[UPGRADE-REHEARSAL.md](UPGRADE-REHEARSAL.md) for installation and recovery.
Recover the complete previous revision and matching environment/image when needed;
editing one installed package is not a verified rollback.
