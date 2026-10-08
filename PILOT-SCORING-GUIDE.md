# Held-out assessments — trainer scoring guide

Trainer/facilitator copy. Revision 1. Do not distribute with participant forms or
load these questions, answers or rubrics into app sources, lessons, prompts or case
banks. They are new multi-record, short-answer exercises covering the same skills;
they are not empirically validated parallel forms. Verify they remain unseen in
the actual course used for each pilot. Semantic independence and equal difficulty
require trainer review; absence of matching text alone does not establish either.

These are public fictional-demo templates, including this answer guide. Keeping the
guide separate during a session does not undo earlier exposure. Confirm participants
have not seen the forms or guide; otherwise prepare fresh private forms and rubrics
and record their versions before assessing independent performance.

## Source contract and approval

These forms apply only to the fictional seed procedure and its built-in receipt
update. Local source references:

- `src/tools/db_queries.py`: seed policy, sections 1–4.
- `src/workflows/readiness_content.py`: critical objective flags and scenario bank.
- `src/workflows/sample_course.py`: diagnostic and assessment bank.
- `src/workflows/change_impact.py`: reviewed demo revision text and updated cases.

Verify the actual approved source before use. The version-one rules are:

1. Each claim requires an itemized receipt; request a duplicate from the supplier
   before submitting when missing. A bank statement alone is insufficient.
2. Submit within 30 calendar days of purchase. Late claims require manager review
   and are not automatically accepted.
3. Above SGD 200, obtain written manager approval before purchase and attach it to
   the claim. Exactly SGD 200 does not trigger this specific above-200 requirement.
4. Finance reviews complete claims within five business days. Correct missing
   information in the returned claim; do not submit the same expense twice.

Version two changes section 1: an itemized receipt or a written Finance exception
under the new rule is accepted evidence. First request a supplier duplicate; if
the supplier cannot provide one, obtain a written Finance exception before
submission. Sections 2–4 are unchanged. No rule here guarantees reimbursement.

Trainer approval: ______  Date: ______  Actual source versions: ______
Forms checked against actual learning banks: ______  Rubric trial completed: ______

## Administration

- Odd participant IDs: A baseline, B post-test. Even IDs: B baseline, A post-test.
- Allow 8 minutes for each form and identical approved-source access. Use 5 minutes
  for U after the version-two refresher. Record actual active time and interruptions.
- Give no item-specific feedback between baseline and post-test. Learning in the
  app continues normally. Collect each form before issuing the next one.
- These forms contain four composite cases, one per objective. Score each case
  using two criteria below. They use free responses rather than the app's choices.
- Readiness objectives 1–3 are critical; claim correction is noncritical in this
  fictional course. Do not infer critical flags for another company procedure.
- Accept equivalent wording and concise answers. Do not require an exact phrase.
  Do not coach during scoring or award extra credit for confident language.
- Award each criterion 1 only when all its stated requirements are present and
  uncontradicted; otherwise award 0. A prohibited action contradicting the criterion
  receives 0 even if a correct action appears elsewhere. No half points.
- Blank answers receive 0. A missing entire stage is missing data, not a zero score.
- If two trainers disagree, preserve both initial scores, discuss against the
  approved policy, record the resolution and apply any clarified rubric consistently
  to all answers. Do not modify a rubric just to make results look better.

## Forms A and B: matched scoring criteria

| Case pair / objective | Criterion 1: 1 point | Criterion 2: 1 point | Critical |
| --- | --- | --- | --- |
| A1 / B1 — receipt_evidence | Identifies the existing itemized receipt for the other purchase as sufficient evidence, and the total-only slip/notification for the deficient purchase as insufficient. | Requires the supplier's duplicate itemized receipt before submission; does not approve bank/payment evidence alone or an invented v1 exception. | Yes |
| A2 / B2 — submission_timing | Identifies the younger claim as within 30 calendar days and the older claim as late; rejects counting only working days. | Routes the late claim for manager review and says acceptance is not automatic; does not promise reimbursement or permanent rejection. | Yes |
| A3 / B3 — prior_approval | Requires written manager approval before the higher-value purchase; verbal/phone approval alone does not meet the rule. | Requires that written approval to be attached to its claim and correctly states exactly SGD 200 is outside this particular above-200 requirement. | Yes |
| A4 / B4 — claim_correction | Corrects the existing returned record by supplying its missing document; does not create a duplicate expense claim. | States five business days for review of a complete claim, with no calendar-day or guaranteed-payment claim. | No |

Each form: total __/8; critical total __/6.
Fully correct cases: __/4; fully correct critical cases: __/3.

Independent critical success requires 6/6 critical points. Report all four cases
separately; a high total cannot override a critical miss. This is the pilot's
assessment outcome and must not write or change app readiness or scores.

## Version-two U1 rubric

Each row is 1 point when fully satisfied, otherwise 0. All four assess the critical
receipt-evidence objective; success requires 4/4.

| Criterion | Required answer |
| --- | --- |
| U1-L | Obtain the available duplicate itemized receipt first, then submit with it; do not skip supplier replacement to seek the exception. |
| U1-M | Receipt evidence is insufficient now. Supplier inability enables seeking a written Finance exception, which must be obtained before submission. Manager approval does not replace it. |
| U1-N | Written Finance exception is sufficient receipt evidence under the stated conditions, so the otherwise complete claim can be submitted; reimbursement is not guaranteed. |
| U1-change | Version one required the duplicate itemized receipt without this fallback. Version two adds the written Finance exception after the supplier cannot provide a duplicate; bank evidence alone remains insufficient. |

Score __/4. Critical objective demonstrated independently: yes only at 4/4.
An overall claim of automatic reimbursement contradicts U1-N even if submission
eligibility is correctly stated elsewhere.

## Recording and interpretation

Use PILOT-RESULTS-TEMPLATE.md. For A/B, record points (__/8), critical points (__/6),
fully correct cases (__/4), and fully correct critical cases (__/3). Percentage is
100 × points / 8. Score change is post-test percentage minus baseline percentage;
one point changes that value by 12.5 percentage points. For U record __/4 separately.

Include criterion-level results so a trainer can identify an actual gap. Record app
readiness separately and investigate any app-ready participant missing a critical
held-out criterion. Report facilitator help and missing stages explicitly. Forms A/B
share a blueprint and differ in details; source reading, form difficulty, practice
and testing effects prevent causal claims about effectiveness from this pilot.

The submitted test forms remain exposed after use. Do not reuse A, B or U as a
fresh retention check for the same participant. Author and approve a new form for
that check. This pack does not include a retention assessment.

## Per-participant score sheet

Participant ID: ______  Trainer: ______  Mode: ______

| Criterion | Baseline form ___ | Post-test form ___ | Evidence / reason for 0 |
| --- | --- | --- | --- |
| Receipt 1 | __/1 | __/1 | ______ |
| Receipt 2 | __/1 | __/1 | ______ |
| Timing 1 | __/1 | __/1 | ______ |
| Timing 2 | __/1 | __/1 | ______ |
| Approval 1 | __/1 | __/1 | ______ |
| Approval 2 | __/1 | __/1 | ______ |
| Correction 1 | __/1 | __/1 | ______ |
| Correction 2 | __/1 | __/1 | ______ |
| Total points | __/8 | __/8 | ______ |
| Critical points | __/6 | __/6 | ______ |
| Fully correct cases | __/4 | __/4 | ______ |
| Fully correct critical cases | __/3 | __/3 | ______ |

| Update criterion | Score | Evidence / reason for 0 |
| --- | --- | --- |
| U1-L | __/1 | ______ |
| U1-M | __/1 | ______ |
| U1-N | __/1 | ______ |
| U1-change | __/1 | ______ |
| Total / critical success | __/4; yes/no | ______ |
