# Demo browser regression checks

These checks exercise the actual FastAPI server and Chromium interface using
fictional seeded content. Each case gets a separate temporary SQLite database,
browser context and localhost server. No existing demo progress is touched;
gateway credentials are cleared and offline mode is enforced.

## Run locally

Use the project's Python 3.13 virtual environment, then run:

```sh
python -m pip install --require-hashes -r requirements-browser.txt
python -m playwright install chromium
python -m pytest browser_tests -q
```

On Linux, use `python -m playwright install --with-deps chromium` when browser
system dependencies are not installed. A working Docker engine is not needed.
Ordinary `python -m pytest -q` still runs the backend suite; browser checks are
explicitly selected because they require downloaded browser binaries.

## Coverage and diagnostics

- Invalid login, keyboard submission, logout and role-specific navigation at
  desktop and 390-pixel phone viewport sizes.
- Missed receipt diagnostic, saved activity resume, source-guided lesson, fresh
  cases and persistent readiness evidence. Reading alone cannot award readiness.
- Trainer source review, approval, draft publication, hidden learner drafts and
  the published course becoming available to a learner.
- Uncaught JavaScript errors fail the test instead of being silently ignored.

This is Chromium regression coverage of the fictional demo, not a full
accessibility audit, Safari/Firefox compatibility check or human pilot result.
The phone case uses a narrow desktop browser viewport, not a physical device.

Failures save screenshots, traces and browser errors under `output/browser/`.
CI uploads that directory on failure and retains it for seven days. To inspect a
trace, run `python -m playwright show-trace output/browser/TEST_NAME/trace.zip`.
Server startup failures include the server log in pytest output. Servers and
browser contexts are closed after each case, including failures.

## Dependency updates

`requirements-browser.in` adds Playwright while constraining application/test
packages to `requirements.txt`. After changing the normal dependency locks,
regenerate this additional lock with Python 3.13 and pip-tools 7.6.2:

```sh
pip-compile --generate-hashes --strip-extras -o requirements-browser.txt requirements-browser.in
```

Install the regenerated lock, install its matching Chromium build, run backend
and browser checks, and submit the update in a feature PR toward `dev`.
