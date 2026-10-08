# AgentX Learn pilot results

Status: NOT RUN. Replace placeholders with observed evidence; do not prefill passes.
Use with [PILOT-TEST-PLAN.md](PILOT-TEST-PLAN.md). Store completed records privately
outside the submission package and public Git repository. Only this blank template
belongs in the public demo pack.

## Run information

| Field | Value |
| --- | --- |
| Pilot dates and timezone | [dates; Asia/Singapore] |
| Coordinator / trainer / facilitator | [owners] |
| App commit | [commit] |
| Source and course versions | [versions] |
| Mode / model | [demo or gateway; model or not applicable] |
| Automated tests / live check | [date, counts, result, evidence; not run if applicable] |
| Held-out forms and rubric versions | [A, B, update form] |
| Agreed criteria / deviations | [criteria approved before testing; deviations] |
| Record access / deletion date | [authorized owners; date] |

## Participant records

Duplicate this block for P01–P10. Keep names and contact details out of this record.

### Participant [ID]

| Field | Observation |
| --- | --- |
| Consent / recording permission | [yes/no; separate permissions] |
| Prior familiarity | [none/some/frequent] |
| Prior exposure to public forms / scoring guide | [no/yes/unknown; replacement form versions if needed] |
| Isolated workspace identifier | [identifier only; no cookies or credentials] |
| Baseline form / source access / active seconds | [A or B; access; seconds] |
| Baseline score / critical score | [points/8; critical points/6; fully correct cases/4; fully correct critical cases/3] |
| Original learning active seconds / pause seconds | [seconds; seconds] |
| App readiness / blocking objectives | [ready/pending/incomplete; objectives] |
| Facilitator interventions | [count and what help was given] |
| Post-test form / source access / active seconds | [other form; access; seconds] |
| Post-test score / critical score | [points/8; critical points/6; fully correct cases/4; fully correct critical cases/3] |
| Score change | [post-test % minus baseline %, in percentage points] |
| Update tested / carried objectives / pending objectives | [yes/no; IDs; IDs] |
| Refresher active seconds / app result | [seconds; result] |
| Updated held-out score / critical score | [points/4; critical success only at 4/4] |
| Optional retention check | [date, fresh form, score, intervening exposure; or not tested] |
| Next step clear? | [1 very unclear–5 very clear; reason] |
| Most confusing interaction | [observation or short anonymized quotation] |
| Issues / missing stages | [IDs and reason] |

## Functional scenario results

| Scenario | Mode | Pass / fail / not tested | Actual result and sanitized evidence | Issue |
| --- | --- | --- | --- | --- |
| F01 Critical gate | [mode] | not tested | [evidence] | [ID] |
| F02 Fresh evidence | [mode] | not tested | [evidence] | [ID] |
| F03 Saved decision | [mode] | not tested | [evidence] | [ID] |
| F04 Supported answer | [mode] | not tested | [claim review] | [ID] |
| F05 Unsupported / review | [mode] | not tested | [evidence] | [ID] |
| F06 Repeated failure | [mode] | not tested | [evidence] | [ID] |
| F07 Reload / duplicate | [mode] | not tested | [evidence] | [ID] |
| F08 Access isolation | [mode] | not tested | [evidence] | [ID] |
| F09 Withdraw approval | [mode] | not tested | [evidence] | [ID] |
| F10 Version update | [mode] | not tested | [evidence] | [ID] |
| F11 Duplicate / stale | [mode] | not tested | [evidence] | [ID] |
| F12 Updated readiness | [mode] | not tested | [evidence] | [ID] |
| F13 Gateway faults | [mode] | not tested | [evidence] | [ID] |
| F14 Dashboard | [mode] | not tested | [evidence] | [ID] |

## Trainer grounding review

| Answer ID | Question type | Claim and source section | Supported / unsupported / uncertain | Correction |
| --- | --- | --- | --- | --- |
| [ID] | [supported/unsupported question] | [sanitized claim; approved source/version/section] | [result] | [action] |

## Summary and decision

- Participants enrolled / started / completed: [counts].
- Original journey completed without help: [count/number attempted].
- All critical held-out post-test items correct: [count/number assessed].
- App-ready participants missing a critical held-out case: [count/number app-ready assessed].
- Updated critical case correct: [count/number assessed after update].
- Individual score changes: [ID: percentage points; include unchanged and lower scores].
- Functional scenarios passed / failed / not tested: [counts; separate modes].
- Grounding: [claims supported/reviewed; unsupported and uncertain counts].
- Trainer time: [source review; corrections; revision review; participant support].
- Missing observations / confounders: [form difficulty, help, exposure, latency, interruptions].
- Decision: [extend pilot / fix and retest / prepare controlled deployment].
- Decision rationale: [evidence and limits; no unsupported effectiveness or savings claim].
- Trainer / technical owner sign-off and date: [names or owner IDs; date].

## Issues and next actions

Severity: blocker = integrity or access failure; major = journey cannot complete;
minor = confusing or inefficient interaction with a working path.

| ID | Severity | Observed problem / reproduction | Expected behavior | Owner | Due date | Retest evidence / status |
| --- | --- | --- | --- | --- | --- | --- |
| [ID] | [severity] | [steps and sanitized evidence] | [expected] | [owner] | [date] | [open/fixed/retested; evidence] |
