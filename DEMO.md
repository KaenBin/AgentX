# Three-minute AgentX Learn walkthrough

After the observed rehearsal, use [PITCH.md](PITCH.md) for the three-minute judging
version with disclosed prepared evidence. The full journey below is best kept for
Q&A. [REHEARSAL.md](REHEARSAL.md) records observed outcomes and timing limitations;
[backup-demo.gif](backup-demo.gif) is a labeled illustrated offline replay.

## Prepare before presenting

The quickest setup is **trainer → Progress → Start fresh live demo** (or the
explicitly labeled offline demo). It opens a separate fictional database as learner,
with the original policy and no completed practice. Use the banner to return to your
main workspace afterward. Nothing is deleted. Tabs in the same browser share the
selected rehearsal. Sign out and use trainer / LearnDemo2026! for the policy update;
the rehearsal remains selected while switching accounts.

The manual option below is useful when you want an entirely separate server port.

Use fictional data only. Rehearse once with a new database so both the original
procedure and its version-two update are available. From the app directory:

```powershell
$demoDatabase = Join-Path (Get-Location) ('data/demo-' + [guid]::NewGuid().ToString() + '.db')
$env:TRAINING_DB = $demoDatabase
$env:AGENT_MODE = 'gateway'
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8014
```

This starts a separate preview and creates a new database without deleting any
existing progress. Gateway mode requires local credentials. For an offline rehearsal,
set `AGENT_MODE=demo` before starting; decision cards explicitly say Offline simulation.
Do not present an offline selection as a live model decision.

Open http://127.0.0.1:8014 and sign in as `learner` with `LearnDemo2026!`.
Choose **Expense procedure readiness — fictional pilot**. Expand **Demo walkthrough**
for the on-screen guide. Use real submitted answers throughout; do not pre-award readiness.

## The story

| Time | Action | What to say |
| --- | --- | --- |
| 0:00–0:40 | Complete the diagnostic; deliberately miss receipt evidence. | “A quiz percentage can hide a critical gap. We track the actual steps this person must demonstrate.” |
| 0:40–1:15 | Continue. Show the receipt lesson and its decision card. | “The agent chooses from approved eligible activities. This card shows the saved evidence and source behind the chosen step.” |
| 1:15–2:00 | Review the lesson and complete fresh cases until ready. | “Reading does not count as mastery. The backend—not the model—checks fresh evidence and every critical objective.” |
| 2:00–2:35 | Sign out. Sign in as `trainer`. Prepare the fictional receipt update in Trainer studio, review its source, lessons and cases, and approve the refresh mapping. | “A policy change makes prior knowledge incomplete. The trainer approves what changed and what evidence remains valid.” |
| 2:35–3:00 | Return as `learner`. Show three carried objectives, complete the updated receipt lesson and a fresh case. | “We retain evidence for unchanged skills and recheck the changed rule. Both procedure versions remain in history.” |

Timing is a rehearsal target; model latency and manual review can take longer.
If time is tight, show the new refresher assignment and finish its case after the pitch.
Do not skip the trainer's content review merely to hit the target time.

## Evidence and limits

Newly issued activities retain their selection mode, eligible-choice count, objective
evidence, source reference and outcome across reloads. Earlier activities have no
retroactively invented decisions. The explanation is a backend summary of observable
evidence, not private model reasoning. Source references are recorded at selection;
historical references do not imply current approval.

Procedure impact comparison is deterministic and trainer-approved. Carried objectives
show accepted prior evidence, not measured minutes saved. This demo does not establish
learning effectiveness or production reliability. If the gateway fails, explain the
error and use a separately labeled offline rehearsal; there is no silent fallback.
