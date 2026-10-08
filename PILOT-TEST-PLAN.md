# AgentX Learn pilot test plan

Status: ready to run; no participant results have been collected in this plan.

## Purpose and scope

Test whether employees can use the app, demonstrate critical procedure steps on
fresh cases, and complete targeted retraining after a reviewed procedure update.
Run with 5–10 volunteers and one trainer. Start with the fictional expense policy.
The current demo uses fictional data only. Company material is deferred until a
company joins and its content, access and gateway data handling are approved.

This is a formative pilot. App readiness is evidence from the app's approved case
bank; independent assessment is a separate trainer-reviewed measure. A small pilot
does not establish certification, general learning effectiveness, or time savings.

## Owners and preparation

- Coordinator: schedule participants, assign anonymous IDs P01–P10, record issues.
- Trainer: approve sources, critical objectives, cases, revision mappings and scoring.
- Facilitator: observe without teaching answers; record each intervention.
- Technical owner: run isolated workspaces, record mode/version and investigate errors.

Before the first participant:

1. Run the Python and dashboard tests using the README commands and the browser
   suite described in [BROWSER-TESTING.md](BROWSER-TESTING.md).
2. Rehearse the complete journey using DEMO.md. If using the gateway, run the
   opt-in live validation once and record its result; it makes model calls.
3. Review [form A](PILOT-ASSESSMENT-A.md), [form B](PILOT-ASSESSMENT-B.md), and
   the [trainer scoring guide](PILOT-SCORING-GUIDE.md). Each form has four composite
   workplace cases covering all four objectives. Agree answer rubrics before testing, and
   keep these prompts out of the app's learning and practice banks. Do not reuse
   app cases or lightly paraphrase exposed questions. Pilot the rubrics with the trainer.
   These templates and answer guide are published in a public repository. Ask whether
   participants have seen them. If so, prepare fresh private forms and trainer-reviewed
   rubrics before assessment; record exposure and form versions. Exposed forms cannot
   establish independent held-out performance.
4. Review the [version-two held-out case](PILOT-ASSESSMENT-UPDATE.md) for the changed receipt requirement. The
   original-version rubric must not be used to grade the updated procedure.
5. Record app commit, course/source versions, mode, model if applicable, and date.
6. Create a fresh isolated rehearsal for each participant. Shared demo accounts
   do not identify 5–10 people: use one workspace per participant, sequentially,
   and map its database identifier to the participant ID. Browser tabs share the
   rehearsal selection. Verify the correct banner before each session.
7. Explain participation is voluntary and results are for product improvement.
   Collect no customer data, credentials or employee names in test records.
   Agree who sees records and their deletion date before starting. Ask separately
   before recording screens or audio.

Do not publish the demo server to give participants remote access. Run this pilot
as supervised local sessions unless deployment and identity controls are already ready.

## Participant session: allow 35–50 minutes

| Stage | Action | Record |
| --- | --- | --- |
| Introduction, 3 min | Explain the task, voluntary participation and think-aloud method. | Participant ID; consent; prior procedure familiarity |
| Baseline, 5–8 min | Give form A to odd-numbered IDs, B to even-numbered IDs. Permit the approved source for both baseline and post-test, with the same time limit. Give no feedback yet. | Correct/total; critical correct/total; elapsed time |
| Learning, 12–18 min | Participant completes the diagnostic naturally, follows coaching, asks one procedure question and completes fresh app cases. Do not instruct them to fail. | Route taken; app readiness; errors; hints; help; elapsed time |
| Post-test, 5–8 min | Give the other held-out form with the same source access and time limit. Trainer scores using the agreed rubric. | Correct/total; critical correct/total; elapsed time |
| Procedure update, 7–10 min | Trainer reviews and activates the fictional receipt update. Participant inspects carried evidence, completes the changed-objective refresher and answers the version-two held-out case. | Carried/pending objectives; refresher result; held-out result; time |
| Debrief, 3 min | Ask what was confusing, whether the next step was clear, and what evidence they trusted. | Ratings and concrete feedback |

If the original course is not ready within the allotted time, record incomplete
and the blocking objective. Do not force a pass. Run the update after completion
in a follow-up session, or mark it not tested. Keep facilitator-assisted outcomes
separate from unassisted outcomes. Record pauses separately from active time.

For any follow-up retention check, use new held-out cases after 3–7 days and
record intervening procedure exposure. Treat this as optional exploratory evidence.

## Functional acceptance scenarios

Run these separately in fresh facilitator workspaces. Deliberate incorrect answers
belong here, not in the participant's baseline or learning assessment.

| ID | Action | Expected result |
| --- | --- | --- |
| F01 | Miss the critical receipt objective, then complete other objectives. | Readiness stays pending until the critical objective is demonstrated. |
| F02 | Follow the receipt lesson and answer a different issued fresh case correctly. | Reading alone awards no pass; fresh reassessment saves objective evidence. |
| F03 | Inspect Why this next step? before and after a reload. | Mode, supporting source, selection evidence and saved outcome remain inspectable. |
| F04 | Ask a supported receipt-policy question. | Answer has an approved-source citation; trainer checks the actual claim against the passage. |
| F05 | Ask an unsupported policy question. | Assistant refers to a trainer; no invented rule or readiness change. Save review request explicitly and verify trainer guidance is persisted. |
| F06 | Fail two fresh cases for one objective. | An open review item is created; resolving it does not itself award readiness. |
| F07 | Reload with an issued activity; submit once, then repeat the same submission. | Progress resumes; repeated identical submission does not duplicate evidence. Changed answers to a submitted activity are rejected. Use API tests if the UI prevents replay. |
| F08 | Switch between learner and alex in the same workspace. | Each learner sees their own history; learner access to trainer actions and another learner's session is rejected. Verify unauthorized IDs through the existing API tests. |
| F09 | Withdraw source approval while a session is active. | Related learning is blocked; historical evidence remains available to authorized viewers. |
| F10 | Complete version one, review and activate the fictional receipt update. | Three unchanged objectives retain labeled prior evidence; the changed receipt objective requires a refresher. Old version history remains. |
| F11 | Repeat activation and try an old-version submission. | No duplicate refresher assignment; stale submission is rejected. Use API tests where the UI cannot issue these requests. |
| F12 | Complete the changed-objective lesson and a fresh updated case. | Correct evidence restores version-two readiness; no old-version receipt pass is relabeled as new evidence. |
| F13 | In a disposable test configuration, trigger a gateway failure or invalid output. | Explicit error; no silent mode switch, invented activity or score change. Use fake-worker tests for controlled faults; never modify shared credentials. |
| F14 | Inspect trainer Progress after the update. | Current and superseded sessions are distinct; carried evidence and outstanding refreshers are counted separately. |

For every scenario record pass, fail or not tested, the actual outcome, evidence,
mode, and issue ID in PILOT-RESULTS-TEMPLATE.md. Offline results do not validate
live model quality. Automated coverage is not an observed participant result.

## Metrics and proposed decision criteria

Agree these pilot criteria before collecting results; they are product goals,
not validated learning standards. Report raw counts and individual scores.

- Functional gates: every executed F01–F14 passes, with coverage evidence for
  scenarios tested through automation. Any not-tested scenario remains an open gap.
- Integrity gates: no exposed answer keys, unauthorized learner records, scoring
  changes caused by the model, silent fallback, or invented policy used as guidance.
- Usability target: at least 80% of participants complete the original journey
  without facilitator help beyond initial login/setup. Report numerator/denominator.
- Readiness target: at least 80% of tested participants answer every critical
  held-out post-test item correctly. Report app readiness beside independent results;
  any participant marked ready who misses a critical held-out case needs investigation.
- Revision target: all participants tested on the update receive the correct
  changed-objective refresher; at least 80% answer the updated held-out case correctly.
- Grounding: trainer reviews each sampled supported answer claim against its source.
  Report reviewed claims/answers and unsupported claims, rather than only valid IDs.
- Trainer effort: record source review, content correction, revision review and
  learner support separately. Do not claim savings without comparable baseline work.

Score change is post-test percentage minus baseline percentage points. Different
forms, source reading and repeated testing can affect it; without a comparison group
do not attribute improvement solely to the app. Report missing results explicitly.

Pause the affected session if an integrity gate fails. Preserve sanitized evidence,
fix the issue and rerun the affected scenarios before continuing that path.

## Closeout

Complete the results template, prioritize observed issues and select a decision:
extend the pilot, fix and retest, or prepare a controlled production deployment.
Record an owner and due date for each action. Keep production identity, access,
hosting and operational work as a separate milestone. A completed test plan is not
a completed pilot: sign off only after recording actual results and unresolved gaps.
