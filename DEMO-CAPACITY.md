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

On **9 October 2026 at 09:13:29 UTC (17:13 Singapore)**, one clean local run of
[`fa1eb92f2eb5cc57e3a1c1fab1d671ecbe8b03c5`](https://github.com/KaenBin/AgentX/commit/fa1eb92f2eb5cc57e3a1c1fab1d671ecbe8b03c5)
passed all three stages and persisted-result checks. Environment: Windows 11 AMD64,
Python 3.13.1, 16 logical CPUs and 33,737,945,088 bytes of host RAM; psutil 7.2.2,
httpx 0.28.1, FastAPI 0.142.4 and Uvicorn 0.54.0. Every stage used five read rounds
and one worker; the owned process tree contained the launcher and application process.

| Learners + trainer | Requests / failures | Startup (ms) | Workload (s) | p50 / p95 (ms) | Peak sampled RSS (MiB) | Average CPU cores | SQLite growth (bytes) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 + 1 | 48 / 0 | 2,195.0 | 1.858 | 16.5 / 36.2 | 56.64 | 0.496 | 0 |
| 5 + 1 | 213 / 0 | 2,086.5 | 5.994 | 58.8 / 183.9 | 59.46 | 0.792 | 36,864 |
| 10 + 1 | 418 / 0 | 2,123.2 | 11.333 | 99.8 / 436.6 | 61.54 | 0.764 | 81,920 |

Report: `output/benchmark/windows-tree-baseline.json` (local, ignored by Git).
SHA-256: `53f777022e7db989aeb701a33a6d9f90a66345113ac58e9c6f335d72b249dab4`.
Save the JSON outside Git with the release record if retaining this evidence.

This single run has no repeat-run confidence interval or enforced CPU/memory limit.
The larger stages averaged more than half a core on this host; a small provider tier
can have different CPU availability and latency. The sampled memory result therefore
does not validate the $7 hosting tier, and the short CPU average does not replace
Railway's full-month usage assumptions. Zero file growth in the smallest stage means
existing SQLite pages accommodated the writes, not that no answers were saved.

The earlier `7b32bb2` Windows run sampled only the virtual-environment launcher.
Its resource readings were invalid, its local report was marked `outcome: invalid`,
and it is excluded from this baseline. The corrected tree sampler and shutdown have
a regression test using a real child process holding a 64 MiB allocation.
