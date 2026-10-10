# Demo release handover

Use this checklist to select a reviewed revision, install the fictional-data
demo, verify recovery and run the first human pilot. Keep the completed operator
and participant records outside Git. This file is a reusable checklist, not a
record that those human actions have happened.

## Reviewed source and evidence

The current application version is `0.3.0`. The reviewed integration baseline is
[`d31f6dd`](https://github.com/KaenBin/AgentX/commit/d31f6dd42953f9aa1ec0ea7056af27da026fe5b9),
merged into `dev` by the owner through
[PR #12](https://github.com/KaenBin/AgentX/pull/12) on 10 October 2026 at 09:37 Singapore.
All seven jobs passed for that integration revision in
[CI run 38013918027](https://github.com/KaenBin/AgentX/actions/runs/38013918027).
Select the full reviewed commit for an installation; a branch name or app version
alone does not identify the installed source. Later changes need their own evidence.

| Evidence | What it establishes | Reference |
| --- | --- | --- |
| Windows and Linux tests | Locked installation and backend/dashboard regression checks | Integration CI above |
| Chromium browser checks | Fictional learner/trainer journeys, keyboard focus, navigation and selected contrast checks | [Browser testing](BROWSER-TESTING.md), [focused review](ACCESSIBILITY-REVIEW.md) |
| Container smoke checks | Container startup, persistent storage, probes and recovery fixtures | [Demo deployment](DEMO-DEPLOYMENT.md) |
| Upgrade rehearsal | Pinned `0.2.0` baseline to selected source, preserved evidence, new writes, restore and matching-backup rollback | [Upgrade rehearsal](UPGRADE-REHEARSAL.md), integration CI above |
| Dependency advisories | Complete known-advisory check for all locked runtime/development/browser Python packages | [Advisory scope and reports](DEPENDENCY-ADVISORIES.md), integration CI above |
| Source bundle | Explicit allowlist, manifest hashes, archive integrity and configured-key exclusion | [Bundle build and retention](SOURCE-BUNDLE.md); use a passing `source-bundle` job from the selected later revision |

For local resource and concurrent-result evidence collected separately from these
integration checks, use [DEMO-CAPACITY.md](DEMO-CAPACITY.md). It does not establish
hosted sizing or human pilot outcomes.

CodeRabbit confirmed and resolved PR #12's source-identity finding. Its docstring
coverage warning remains advisory; its green status does not waive the limits
of the dependency scan. Earlier release reviews are recorded in [RELEASES.md](RELEASES.md).

CI reports and the source bundle are retained for 14 days. Before expiry, save
the selected run's `demo-upgrade-rehearsal`, `demo-capacity-benchmark`,
`dependency-advisories` and, when its packaging job is present, `demo-source-bundle`
artifacts with the private release record. Record the run, source commit and
checksums. Packaging CI is a follow-up to the seven-job baseline above; do not
attribute its artifact to that earlier run. Reports contain safe fixture outcomes; they do
not replace a backup of the operator's actual data. See the upgrade guide for
its fields and limits.

## Select and install

- [ ] Owner selects the reviewed full commit and records its CI run and limitations.
- [ ] Operator retains that run's source bundle/reports before artifact expiry and
      verifies the ZIP checksum before extraction, where using a bundled installation.
- [ ] Operator records the machine, installation time and chosen offline/live mode.
- [ ] Operator verifies Python 3.13, or Docker with Compose for a container install.
- [ ] Existing demo data is backed up with the app stopped before an update.
- [ ] Prior source/image identity and its matching backup are available for rollback.
- [ ] Operator installs using [README.md](README.md#start-locally) or
      [DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md#container-installation).
- [ ] Operator records the full commit, app version and locally built image ID where
      applicable. Local image IDs are not registry digests.
- [ ] `/ready` succeeds; operator signs in, checks saved evidence, submits an activity
      and verifies persistence after reload.
- [ ] Learner and trainer paths work in the selected installation. Live mode requires
      its own successful gateway check; offline results do not establish live behavior.
- [ ] Recovery is exercised in separate empty storage, and the operator records the
      restored evidence. Follow the existing stopped-app restore instructions.

Use [DEMO-OPERATIONS.md](DEMO-OPERATIONS.md#record-an-update) for the installation
record and request-ID diagnostics. Do not erase the normal demo volume to perform
a rehearsal. Preserve actual backups and private records outside the repository.
The container setup uses one worker, persistent SQLite storage and localhost access.

## First volunteer and trainer session

- [ ] Owner confirms a volunteer and trainer, session date and private record location.
- [ ] Trainer reviews the fictional source, objectives, critical steps and assessment forms.
- [ ] Facilitator checks prior exposure to public forms and prepares private alternatives
      where needed. Keep answer guides out of participant view.
- [ ] Facilitator creates and identifies an isolated rehearsal workspace, checking its banner.
- [ ] Facilitator uses the [run sheet](PILOT-FACILITATOR-RUN-SHEET.md) and records
      consent, interruptions, assistance, incomplete stages and actual scores.
- [ ] Keyboard and narrow-screen journeys are observed. Actual screen-reader speech,
      browser zoom, forced colors and physical-device behavior are checked and recorded
      where available; untested conditions remain explicitly untested.
- [ ] Trainer reviews critical held-out misses, particularly when the app reports readiness.
- [ ] Owner records blockers, owners and retest outcomes using the
      [results template](PILOT-RESULTS-TEMPLATE.md). Automated fixtures are kept separate.

No human pilot results or actual operator installation/recovery record have been
collected in this handover. They require the people performing those actions.

## Decide the next release

The owner reviews actual installation, recovery and pilot outcomes before expanding
the demo. Fix observed blockers through branches from `dev`, request review and retain
the passing CI evidence. Only the owner merges and promotes `dev` to production
`master`. Keep the approved revision and rollback information together.

If remote access becomes necessary, review the dated
[hosting options and estimate](DEMO-HOSTING-OPTIONS.md), including its usage assumptions,
access restrictions and provider-specific recovery work. Recheck prices, add the
access/backup costs and obtain the owner's provider, budget and deployment decision.
No hosting provider, paid plan or external deployment is selected by this checklist.

When a company joins, revisit identity, data handling, content ownership and support
requirements in [PRODUCT-DELIVERY-PLAN.md](PRODUCT-DELIVERY-PLAN.md). The separate
[production checklist](PRODUCTION-RELEASE-CHECKLIST.md) remains unverified; this demo
handover does not establish production readiness.
