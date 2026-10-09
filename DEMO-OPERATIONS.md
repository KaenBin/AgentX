# Diagnose and support the fictional-data demo

Use with [DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md) for installation, updates and
backup/restore. [RELEASES.md](RELEASES.md) records application versions and review
references. This is a local fictional-data demo with shared accounts.

## Liveness and readiness

| Endpoint | Success | Failure | What it establishes |
| --- | --- | --- | --- |
| `GET /health` | 200, `status: ok` | Connection/startup failure; an invalid rehearsal cookie can return 400 | The HTTP process responds; it does not check the database |
| `GET /ready` | 200, `status: ready`, main mode and app version | 503, `status: not_ready`, `Database unavailable` | The main SQLite database can be read and the required core tables exist |

Both endpoints are unauthenticated and expose no database path, account or gateway
credential. `/ready` ignores rehearsal cookies and request-local database overrides;
it always probes the main deployment. `/health` retains its existing mode behavior,
which follows a selected browser rehearsal. Container probes carry no cookies.

Readiness opens an existing database in read-only mode, with a one-second SQLite
lock wait per statement. It does not create a database, seed data or call the model.
It is a small read/schema check, not an integrity scan, write-permission test or
gateway availability check. Startup still initializes a configured demo database;
readiness does not replace that startup behavior.

Docker's health check uses `/ready`. After startup or an update:

```sh
docker compose ps
curl -i http://127.0.0.1:8010/ready
```

Use `curl.exe` in Windows PowerShell. If `/health` succeeds but `/ready` fails,
check the container state, volume mount, configured database and UID 10001 access.
A brief exclusive SQLite lock can cause a temporary 503; check again after the
write/maintenance operation completes. Persistent missing/corrupt/schema failures
need investigation and, if appropriate, restoration of a verified matching backup.
Do not create an empty database or delete the data volume as a diagnostic shortcut.
Docker marks repeated failed probes unhealthy; its restart policy does not itself
restart a running container solely because its health status is unhealthy.
See [Docker restart policy behavior](https://docs.docker.com/engine/containers/start-containers-automatically/).

## Request IDs and logs

Each HTTP request receives a new server-generated `X-Request-ID` response header.
Incoming IDs are not reused. Unexpected errors before the response starts return a
generic 500 JSON error with the same ID, so the operator can correlate the failure.
Existing handled validation, permission and gateway responses keep their behavior.

The dedicated `agentx.http` logger writes JSON lines to stderr. Fields are:
`event`, UTC `timestamp`, `level`, `request_id`, `method`, `route`, `status_code`,
`duration_ms` and `error_kind`. `route` is the matched route template, such as
`/api/learning/{sid}`, rather than a submitted URL or identifier. Early guard errors
and unmatched routes use `<unmatched>`. Unknown HTTP methods use `OTHER`.

Application request logs exclude bodies, query strings, headers, cookies, account
names, source/chat content, database paths, exception messages and original stack
traces. The Docker launcher, `start.ps1`, README/DEMO commands and browser test
launcher disable Uvicorn's raw access log. For a custom Uvicorn command, also pass
`--no-access-log`. This policy covers application HTTP diagnostics; startup messages,
other tools, browser traces and screenshots require their own handling.

Inspect recent container logs and search for an observed request ID:

```sh
docker compose logs --tail 100 app
```

| `error_kind` | Interpretation | Next step |
| --- | --- | --- |
| `database_unavailable` | Main-database readiness failed | Check data mount/access, locks and schema; follow the verified restore runbook if needed |
| `gateway_unavailable` | A handled model gateway error returned 503 | Check approved gateway configuration and provider status; readiness does not test the provider |
| `unhandled_exception` | Unexpected failure before response headers | Preserve request ID, time, app revision and safe reproduction steps; investigate using fictional fixtures |
| `response_interrupted` | Failure after headers were sent | The original status may remain 200; investigate as an error and do not assume the operation completed |
| `server_response` | Other 5xx response | Use the request ID and route to reproduce and classify the failure |

Normal requests, including probes and expected 4xx responses, log at INFO. Server
failures log at ERROR. An interrupted response cannot be replaced: its log retains
the status actually sent, and the re-raised server error carries only a generic
message and request ID. A logging sink I/O failure is discarded so it cannot change
the result of a learning write. These logs intentionally trade exception detail for
privacy; debug with isolated fictional fixtures instead of turning on raw payload logs.

## Record an update

Before installing a reviewed revision, record the app version, Git commit, local
image ID, configured mode, backup location, operator and time. Record image identity
after building with `docker compose images`. A locally built tag is not an immutable
registry digest. Keep credentials and the actual backup outside the repository.

Use the existing [update and rollback instructions](DEMO-DEPLOYMENT.md#updates-and-rollback).
After updating, verify `/ready`, sign in, inspect saved progress and run the relevant
learning journey. Record the outcome and any rollback. A green probe alone does not
establish learning correctness or successful recovery.

Stop and investigate failed authentication, missing history, wrong procedure content
or writes that cannot be confirmed. Use the prior reviewed commit and its matching
backup for rollback; older code is not guaranteed to accept a newer database.
The owner approves all merges and any external deployment. Human pilot results and
company production controls remain separate, unverified milestones.
