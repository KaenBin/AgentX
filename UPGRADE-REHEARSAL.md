# Demo upgrade and recovery rehearsal

This automated fictional-data exercise checks the reviewed `0.2.0` baseline at
[`8c5a357`](https://github.com/KaenBin/AgentX/commit/8c5a357043fbfa5e562b49afc693894e5f3d435b)
against the current checked-out demo. The baseline is the merged source before
the `0.3.0` operability work. These are source revisions, not evidence that an
earlier production installation existed.

## What the exercise verifies

`upgrade_smoke.py` builds two images with unique local tags. It starts the old
image in a disposable Compose project, completes a learning session with an
initial wrong answer and subsequent coaching, and saves a second participant's
issued but unanswered activity. A separate browser rehearsal creates companion
files in the volume. All API calls use offline mode and fictional seeded accounts.

The script stops the app and copies the whole volume before upgrading. It then:

1. Starts the current image on the same volume and checks its API version and `/ready`.
2. Checks completed and in-flight learning views, then compares all saved table
   columns and rows except rotating authentication sessions. User accounts,
   sources, courses, activity IDs, scores, decisions and relationships are included.
3. Compares hashes of companion files, including the separate rehearsal database.
4. Submits the pending answer through the upgraded app and copies another stopped backup.
5. Replaces only its disposable volume, restores that new backup with the supported
   recovery helper, and checks the new answer and saved rows again.
6. Restores the original backup into a second empty disposable project, then runs
   the old image. It verifies the original evidence and unanswered activity.

Each copied database must pass SQLite integrity and foreign-key checks. Rollback
uses the old image **and its matching old backup**; it deliberately excludes the
answer submitted after the upgrade. It does not establish that old code can read
a newer schema or retain new writes while reverting to an earlier snapshot.

## Run locally

Use Python 3.13, Git and a responsive Docker engine with Compose. The host needs
only the Python standard library; application dependencies run inside the images.
Commit tracked changes before running so the reported revisions identify the tested
source. Create a separate baseline checkout, then run from the current project:

```sh
git clone --no-checkout https://github.com/KaenBin/AgentX.git ../agentx-upgrade-baseline
git -C ../agentx-upgrade-baseline checkout --detach 8c5a357043fbfa5e562b49afc693894e5f3d435b
python upgrade_smoke.py ../agentx-upgrade-baseline
```

The script refuses a different baseline or tracked modifications in either checkout.
It allocates localhost ports and unique `agentx-upgrade-*` projects; cleanup removes
only those projects' disposable volumes and the two uniquely tagged images. It does
not operate on the normal `agentx-demo` volume. If cleanup fails, inspect the named
rehearsal projects before retrying. Do not substitute your real data for the fixtures.

The supported restore helper now also accepts explicit Compose files through its
Python API. This lets the rehearsal select the tested image for both its stopped-app
check and extraction. The normal `python restore_demo.py ./demo-backup` command
and its refusal to restore into active or non-empty storage retain their behavior.

## CI evidence and limits

The `upgrade` job in `.github/workflows/test.yml` checks out the pinned baseline
separately, runs the real Docker exercise and uploads `demo-upgrade-rehearsal` only
after a successful run. The JSON report is retained for 14 days and records UTC time,
source commits, app versions, local image IDs, named outcomes, baseline row counts,
a snapshot hash and companion-file count. It excludes raw rows, passwords, cookies,
policy text and backup files. Local reports are written under ignored `output/upgrade/`.
Archive an approved report with the release record if longer retention is needed.

A passing report proves this exact revision pair and these fictional workflows.
Changing the baseline, schema or learning contract requires a reviewed update to
the fixture and comparison rules. This exercise provides no hosted-deployment,
human learning, production recovery-target or real employee-data evidence.
An operator still records their actual installation using
[DEMO-OPERATIONS.md](DEMO-OPERATIONS.md#record-an-update) and follows the
[backup and rollback runbook](DEMO-DEPLOYMENT.md).
