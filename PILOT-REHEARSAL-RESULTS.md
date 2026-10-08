# Pilot preparation rehearsal — 8 October 2026

Observed run: 12:52 Singapore time. Mode: offline demo.
Type: automated backend rehearsal with known fixture answers. Participants: zero.

## Results

| Check | Result |
| --- | --- |
| Missed receipt diagnostic blocks readiness | Pass |
| Receipt coaching lesson becomes eligible | Pass |
| Fresh cases reach original-version readiness | Pass, score 100 |
| Saved decisions remain inspectable and labeled demo | Pass |
| Revision comparison requires receipt-objective refresh | Pass |
| Three unchanged objectives carry prior evidence | Pass |
| Successor remains pending at 75 percent | Pass |
| Updated fresh case restores version-two readiness | Pass, score 100 |
| Superseded history and original decisions remain preserved | Pass |

Evidence is retained outside the application database:
`../pilot-rehearsal-6337539bea534340906bb0501576a4a1/report.json`
and its adjacent `rehearsal.db`. No existing application progress was changed.
This path identifies local historical evidence; the database and filled report are
excluded from the public repository and source bundle.

The runner is [pilot_rehearsal.py](pilot_rehearsal.py). From the workspace parent:

```powershell
.\employee-training-assistant\.venv\Scripts\python.exe employee-training-assistant/pilot_rehearsal.py
```

Each run creates and retains a uniquely named database directory under the current
working directory. Run in a writable location. It uses development dependencies
and existing test fixture helpers. It uses known answers and automatically activates
the exact fictional revision mapping; that is not a trainer's human content review.
An assertion failure stops the run without producing a passing report.

Publication check: rerun on 8 October at 23:48 Singapore time. All nine backend
checks passed again, with zero participants. Fresh local evidence is in
`../pilot-rehearsal-2457a2f9b63c49ceb004aef9d1d56b20/report.json`; it is excluded
from the public pack. The earlier browser observations below were not rerun by
this command.

An initial run completed the workflow but failed to format its report because the
Windows runtime lacked timezone data. The runner now uses Singapore's UTC+08:00
offset and the subsequent complete run passed. This was a rehearsal-runner issue.

## What remains untested by this rehearsal

- Browser usability, visual presentation and actual page reload behavior.
- Live gateway behavior, answer grounding and model quality.
- Participant completion times, held-out scores and learning outcomes.
- Human trainer approval of the content, assessment forms and revision mapping.

The other acceptance scenarios remain subject to their individual test evidence.
This rehearsal does not mark every F01–F14 scenario passed. Participant results
must stay NOT RUN until actual sessions occur.

## Next execution step

Use [PILOT-FACILITATOR-RUN-SHEET.md](PILOT-FACILITATOR-RUN-SHEET.md) for one supervised
human rehearsal. Obtain trainer approval of the held-out forms and rubric, then
schedule participant sessions. Record each observation in the results template.

## Browser rehearsal — 8 October 2026, approximately 12:59–13:02 SGT

Completed through the local browser at `http://127.0.0.1:8016` in a separate
fictional database. The agent operated learner and trainer accounts using known
policy answers. This is agent-operated browser testing, not a volunteer session.

Observed passes:

- Incorrect receipt diagnostic showed its gap; correct diagnostics still required fresh cases.
- Targeted receipt lesson was selected, with a source and saved decision explanation.
- Browser reload retained the issued lesson and decision record.
- Reviewing the lesson explicitly said readiness was not awarded.
- Four fresh objective cases produced original-version readiness.
- Trainer could inspect the diff, complete updated source, all lessons and answer keys.
- Activation assigned the receipt refresher and preserved three unchanged objectives.
- Updated lesson plus fresh Finance-exception case restored version-two readiness.
- Learner Progress showed the original version as superseded and the new version ready.
- Trainer Progress showed one current ready session, three carried objective records,
  one assigned refresher and zero outstanding refreshers.
- Start fresh offline demo opened a separate, not-started original-policy workspace.

Evidence: [version history screenshot](pilot-browser-evidence.jpg) and
[clean session screenshot](pilot-session-ready.jpg).

No workflow blocker was observed on this path. Minor observation BR-01: the
version-two procedure displays “Rule version 1” (and “Rule 1” in Progress), referring
to the scoring-rule schema. This could be confused with the procedure version.
Record whether the volunteer understands it before deciding on a wording change.

Human review and held-out assessment have not been performed. The user will arrange
the volunteer and trainer. No participant completion time or assessment score has
been recorded. Live gateway and the other acceptance paths were not exercised here.

### Prepared first session

At the end of the recorded rehearsal, the local server used port 8016 and the browser
was left in a fresh offline workspace as learner, at “not started.” This is historical
session state, not a guarantee that the server is still running or the workspace is
still clean. Check the current banner and database before each participant session.
The loopback address works only on the host computer while its server is running.

Use P01 for the first volunteer: form A baseline, form B post-test, then form U
after the reviewed update. Trainer approval of the forms/rubric and voluntary
participation must occur before collecting results. Give baseline first; do not
start the app diagnostic until the baseline form is collected. Use the facilitator
run sheet, and keep the trainer scoring guide out of participant view. Confirm the
volunteer has not seen the public forms or answer guide; if exposed, use fresh private
forms approved by the trainer instead.

If the server stops, restart using DEMO.md's separate-database instructions and
create a fresh offline rehearsal. Do not assume a different running app has this
same clean workspace or the same database.
