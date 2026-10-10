# Demo operator record — blank template

Copy this template to a private location outside the repository before filling it
in. It records an actual fictional-data installation or update; it is not a
completed release record. Keep credentials, databases, learner details, chat/source
text and completed pilot forms out of this file and out of Git or CI artifacts.
The blank template is distributed in the source bundle.

Use [the release handover](DEMO-RELEASE-CHECKLIST.md) to select the source and
[the deployment runbook](DEMO-DEPLOYMENT.md) for container installation, stopped-app
backup, restore and matching-backup rollback. For a bare-Python installation, use
[README.md](README.md#start-locally); the container recovery helper does not establish
bare-Python recovery. Record the procedure actually exercised. Follow
[operations guidance](DEMO-OPERATIONS.md) for readiness and request-ID diagnostics.

Replace bracketed fields with actual observations. Every check starts **untested**;
use **pass**, **fail**, **untested** or **not applicable**, with a reason and evidence.
CI fixture outcomes belong in the source-evidence section, not in operator results.
Record timestamps with a timezone. Repeat this record for each installation/update.

## Source selection and retained CI evidence

| Field | Actual value |
| --- | --- |
| Record ID; operation (new installation / update / recovery drill) | [fill in] |
| Owner selecting source; selection time | [fill in] |
| Repository URL and full reviewed source commit | [fill in] |
| Review PR; passing `push` CI run for that merged `dev` commit | [fill in] |
| App version declared by that source | [fill in] |
| Source acquisition (Git checkout / CI ZIP); retained source location | [fill in] |
| CI artifact names and private retained locations; retention time | [fill in] |
| ZIP SHA-256, where used; expected checksum reference; actual comparison result | [fill in or not applicable with reason] |
| Limits of the selected CI evidence; checks not run | [fill in] |

Select the full commit, not merely `dev` or `0.3.0`. For a ZIP install, retain and
verify the selected run's artifact before its 14-day expiry. A PR bundle can contain
a temporary merge commit; use the merged `dev` push run for installation evidence.
Hashes detect mismatches against the retained checksum, not publisher authenticity.
See [source-bundle provenance and checks](SOURCE-BUNDLE.md).

## Installation context and update preparation

| Field | Actual value |
| --- | --- |
| Operator; machine identifier; OS/version | [fill in] |
| Python version; Docker/Compose versions where used | [fill in] |
| Installation start/end times | [fill in] |
| Installation path; local URL/port; Compose project/storage identity where used | [fill in] |
| Configured mode (offline demo / gateway); gateway checks where applicable | [fill in; no credentials] |
| Built image ID where used; source commit actually installed | [fill in] |
| Prior source commit/image ID and prior app version for an update | [fill in or not applicable with reason] |
| Stopped-app backup time and private location; matching prior revision | [fill in or not applicable with reason] |
| Recovery/rollback procedure selected; compatibility limits | [fill in] |

The current container workflow is localhost-only, one worker and persistent SQLite.
A locally built image ID is not a registry digest. Before updating existing data,
retain the prior reviewed source/image and its matching stopped-app backup. Do not
assume prior code accepts a database modified by newer code.

## Actual installation checks

| Check | Result | Observed time; evidence or reason |
| --- | --- | --- |
| Installed source/image identity matches the selected revision | untested | [fill in] |
| `/ready` returns ready with the expected app version and mode | untested | [fill in] |
| Learner and trainer sign-in work | untested | [fill in] |
| Expected procedure version and saved learning history are present | untested | [fill in] |
| A fictional activity submission is saved and survives reload | untested | [fill in] |
| Container recreation preserves the saved result, where applicable | untested | [fill in] |
| Learner journey and trainer version-update journey work | untested | [fill in] |
| Gateway behavior is verified, if gateway mode was selected | untested | [fill in] |

Offline results do not establish live-model behavior. A successful readiness probe
does not establish successful writes or learning correctness. Reference safe
record IDs or private evidence locations; do not paste participant data or logs
containing credentials. Preserve request IDs and timestamps when diagnosing faults.

## Actual recovery and rollback evidence

Perform the recovery drill in separately identified empty storage, with the app
stopped. Preserve the normal installation and its data. Record the target project,
volume/path and port before executing any restore or cleanup. Follow the runbook's
empty-storage and stopped-app requirements; do not erase normal data for a drill.

| Field or check | Result | Actual value or evidence |
| --- | --- | --- |
| Backup source revision, stopped-app time and private location | untested | [fill in] |
| Separate recovery target; confirmation app stopped and storage empty | untested | [fill in] |
| Recovery start/end times; observed duration | untested | [fill in] |
| Restored app readiness, version and learner/trainer sign-in | untested | [fill in] |
| Expected procedure and saved evidence restored | untested | [fill in] |
| A new fictional write succeeds after recovery and survives reload | untested | [fill in] |
| Matching-backup rollback to prior source, if actually exercised | untested | [fill in or not applicable with reason] |
| Drill cleanup and confirmation normal installation is preserved | untested | [fill in] |

A backup file alone is not verified recovery. Record failures and interruptions,
including an incomplete restore; do not start a partially restored target. Do not
claim rollback was exercised if only the current revision was restored. This record
does not establish production recovery targets or off-machine backup coverage.

## Outcome and follow-up

- Installation/recovery outcome and limitations: [fill in; initially untested].
- Blockers, safe reproduction steps, request IDs and private evidence references:
  [fill in; include failed or incomplete checks].
- Follow-up owner, issue/PR reference and retest outcome: [fill in].
- Actual rollback, if performed, and final running source/image identity: [fill in].
- Owner decision, decision time and conditions: [fill in; no automatic approval].
- Human pilot record reference: [fill in or not yet collected]. Use the separate
  [pilot results template](PILOT-RESULTS-TEMPLATE.md); CI is not participant evidence.

The owner controls merges and promotion to production `master`. This record does
not authorize external deployment, spending or company production use.
