# Production release acceptance checklist

Status: NOT VERIFIED. Attach actual evidence; checkboxes are not implementation.
Use with PRODUCT-DELIVERY-PLAN.md. Scope: first invited organization deployment.

This checklist applies when a company joins; it does not block the current
fictional-data demo. Demo deployment and browser CI are documented in
[DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md) and [BROWSER-TESTING.md](BROWSER-TESTING.md).
Those checks cover part of the foundation; they do not verify these production gates.

Release: ______  Commit: ______  Image digest: ______  Date: ______
Environment: ______  Owner: ______  Change/release record: ______

## Product and content

- [ ] Launch users, assigned procedures and support scope are documented.
- [ ] Human pilot completed; critical gaps and usability blockers resolved or launch narrowed.
- [ ] Actual source/courses/cases approved by named trainer; held-out cases unexposed.
- [ ] Assignments include unstarted users; current and historical readiness remain distinct.
- [ ] Withdrawal, case exhaustion and revised-procedure paths demonstrated.
- [ ] Learner/trainer/admin onboarding and known limitations documented.

## Identity, access and privacy

- [ ] Managed identities and explicit memberships work; shared demo accounts disabled.
- [ ] Organization and object authorization tested across reads, writes, exports, jobs and AI.
- [ ] Offboarding/revocation rejects new access without corrupting historical evidence.
- [ ] HTTPS/proxy/session/CSRF/origin controls and request/login limits verified.
- [ ] Production demo seed, rehearsal endpoints and demo credential paths disabled.
- [ ] Gateway data flow, processing location, access and provider arrangement reviewed.
- [ ] Retention, export, deletion and backup-expiry behavior approved and documented.
- [ ] Secret/dependency/container scan findings triaged; no unresolved launch blockers.

## Build and deployment

- [ ] Locked build reproduced on a clean runner; runtime/test dependencies separated.
- [ ] Python, dashboard, browser and PostgreSQL integration suites pass.
- [ ] Immutable image, SBOM, configuration contract and release manifest retained.
- [ ] Staging and production resources/credentials separated; IaC changes reviewed.
- [ ] Same tested image digest promoted; runtime/migration/CI permissions separated.
- [ ] Production environment validation passes without leaking secrets.
- [ ] Smoke checks exercise login, source access, answer submission and trainer inspection.
- [ ] Staffed rollout window, stop conditions and previous compatible image recorded.

## Data and upgrades

- [ ] Database schema compatibility is recorded for old and new application versions.
- [ ] Versioned migrations execute once under controlled locking.
- [ ] Upgrade from the previous supported schema passes on representative data.
- [ ] Legacy import preserves counts, links, decisions, objective results and history.
- [ ] Backfills verified; destructive steps separated and explicitly reviewed.
- [ ] Backup/PITR evidence and timed restore meet approved RPO/RTO.
- [ ] Application rollback rehearsed; database forward-repair/restore conditions documented.
- [ ] Content/model rollback consequences understood; no historical scores overwritten.

## AI and reliability

- [ ] Approved model/prompt/tool/retrieval versions recorded with evaluation dataset.
- [ ] Trainer claim-support review and unsupported/injection/access cases meet approved criteria.
- [ ] Model cannot change grades, approval, assignments or readiness directly.
- [ ] Total request deadline, bounded retries, concurrency and usage caps tested.
- [ ] Provider failure is explicit; deterministic learning remains usable where intended.
- [ ] Usage/cost unknowns are labeled; disable and previous-config recovery paths work.
- [ ] Representative mixed workload meets approved availability/latency/capacity targets.

## Operations and handoff

- [ ] Liveness/readiness probes and core-journey synthetic checks work.
- [ ] Redacted telemetry covers errors, writes, provider calls and budget limits.
- [ ] Alert delivered to actual owner; escalation and staffed support hours published.
- [ ] Deploy, migration, restore, access incident and unsafe-content runbooks reviewed.
- [ ] Incident exercise completed; primary/substitute owners can execute recovery.
- [ ] Release notes, user communications, changelog and maintenance schedule ready.
- [ ] Post-release review time and metrics agreed; monitoring completed before closure.

## Decision and evidence

| Gate | Evidence link / result | Accountable sign-off |
| --- | --- | --- |
| Product/content | ______ | Product owner / trainer: ______ |
| Access/privacy | ______ | Responsible reviewer: ______ |
| Build/deployment | ______ | Technical/platform owner: ______ |
| Data/recovery | ______ | Backend/platform owner: ______ |
| AI/quality | ______ | AI/content/QA owner: ______ |
| Operations | ______ | Support/operations owner: ______ |

Decision: NO-GO / GO FOR INVITED USERS. Date: ______
Unresolved gaps and impact: ______
Approved launch boundary and follow-up owners/dates: ______

Do not waive access, integrity, recovery or unsupported production-data-processing
blockers by marking them “accepted.” Narrow scope or fix and retest. Other deviations
need named ownership, impact, expiration and a compensating measure in the release record.
