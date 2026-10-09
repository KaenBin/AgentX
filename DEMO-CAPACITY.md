# Measure fictional demo capacity

`benchmark_demo.py` runs the current offline application as a single Uvicorn worker
on an unused localhost port. Each stage creates its own temporary SQLite database
and distinct synthetic learners, alongside one trainer client. It never accepts a
target URL or existing database path. Inherited database and gateway settings are
overridden; no model calls are made.

## Run and preserve evidence

Run from a **clean Git checkout** of the repository with Git available, the locked
development installation and Python 3.13. The deployment ZIP includes the tool for
reference but has no Git history, so run measurements from the checkout rather than
an extracted ZIP:

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.txt
.\.venv\Scripts\python.exe benchmark_demo.py --learners 1 5 10 --read-rounds 5 --output output/benchmark/run-UNIQUE.json
```

On Linux, use `.venv/bin/python` for the same commands. Choose a new output filename
for every run. The script refuses to overwrite previous evidence and rejects tracked
changes or untracked benchmark/application inputs before starting. Reports record
the full source commit, Python/dependency versions, OS, architecture, logical CPU
count and host memory, without hostname or database paths.

The server and its temporary data are stopped/removed on success and handled failure.
Only the aggregate JSON report remains. A failed run returns a nonzero exit code and,
when report creation succeeds, records `outcome: failed` and the failed stage.
Startup failure, malformed responses, unexpected statuses, sampling failures and
incorrect saved evidence prevent a passing report. Interruptions can leave an
incomplete report; require valid JSON and `outcome: passed` before using it as evidence.
Keep valuable reports with the private release record outside Git; `output/` is ignored.

## Workload and correctness

At each configured learner count, all learner journeys and the trainer task start
together. Each learner signs in, reads state repeatedly, starts the fictional readiness
course, deliberately misses the first diagnostic, completes remediation and fresh cases,
reloads saved progress after every answer and reads final state before signing out.
The trainer signs in and reads state alongside the learners, then checks the complete
session set. Learners attempt to read another learner's session and must receive 403
when there is more than one learner. With one learner, state scoping is checked but
there is no second synthetic learner for the cross-user denial probe.

The tool verifies deterministic scores, critical-objective readiness and saved API
state. After stopping the server it compares persisted session owners, issued answer
values and scores with the submitted evidence and checks SQLite integrity/foreign keys.
Synthetic accounts and answer-bank access exist only in disposable benchmark storage;
they do not change the app's account or grading behavior.

`--read-rounds` controls state reads before and after each learner's journey, plus
the trainer's initial reads. Defaults are 1, 5 and 10 learners with 5 read rounds.
Limits are 1–100 learners and 1–1000 read rounds. The reported learner count has
**one additional trainer client**. A concurrency level describes started clients;
it does not guarantee every client has an in-flight request at every instant.

## Interpret the measurements

| Field | Meaning and limit |
| --- | --- |
| `startup_ms` | Process launch through successful main `/ready`, including creation/seeding of a fresh database; excludes later synthetic-account setup |
| `workload_seconds` | Concurrent HTTP workload through correctness checks over the API and logout; excludes startup, fixture setup and stopped-database verification |
| Request count/error rate | Timed workload requests only; expected isolation 403s count as successful checks; readiness polling and harness-cancelled requests are excluded; cancellations are reported separately |
| p50/p95 latency | Nearest-rank percentiles of observed request durations in milliseconds, overall and by operation; small samples have limited statistical value |
| Peak sampled RSS | Maximum sum of resident memory in the owned server process tree, observed every 100 ms during startup and workload; short peaks can be missed |
| CPU seconds/average cores | Server-tree user + system CPU consumed during the workload, divided by workload wall time for average cores; 1.0 means one core fully used on average |
| Database growth | Main SQLite file size after clean shutdown minus size after fixture setup; not a monthly storage forecast |

Resource measurements cover the server and its owned descendants, including Windows
virtual-environment launchers. Shared pages may be counted in more than one process.
RSS is resident memory, not container/account billable memory; CPU excludes the load driver. Host OS, hardware,
other processes, Python versions and filesystem behavior affect results. The load
driver shares the host with the server. See the primary
[psutil API reference](https://psutil.io/api/) for process memory and CPU semantics.

This is a short API benchmark on fresh small databases. It does not measure browser
rendering, internet/proxy latency, model usage, long-running leaks, realistic learner
think time, large historical data, provider CPU/memory limits or sustained maximum
capacity. Repeat runs on a controlled environment and on the selected host are needed
before establishing service targets or selecting a memory tier.

CI runs the full 1/5/10 workload on an Ubuntu runner and preserves aggregate results
for 14 days as `demo-capacity-benchmark`. Correctness and cleanup regressions run in
the regular Windows/Linux suite. CI gates functional correctness; it has no absolute
latency or memory threshold because runner performance varies. Save an approved
artifact, its run, full source revision and checksum before it expires.

## Local baseline

Use a clean committed run's JSON report as the baseline evidence. Provider sizing remains an open validation step in
[DEMO-HOSTING-OPTIONS.md](DEMO-HOSTING-OPTIONS.md). Human pilot outcomes remain
separate evidence in the [release handover](DEMO-RELEASE-CHECKLIST.md).
