# AgentX Learn

## One-line description

An evidence-based training agent that coaches missed procedure steps and assigns
targeted refreshers when approved guidance changes.

## Short submission description

Course completion does not tell a trainer whether an employee can apply every
critical step—or whether that evidence still applies after a policy update.

AgentX Learn connects approved company guidance, learner diagnostics, targeted
coaching and fresh scenario assessments. The agent selects eligible activities
using saved learner evidence. The application validates every selection and grades
answers deterministically; the model cannot award readiness or publish policy.

When a procedure changes, a trainer reviews the revised source, lessons, cases and
impact mapping. Evidence for unchanged objectives can carry forward, while affected
objectives require fresh practice. A dashboard exposes critical gaps, open reviews,
version history and the decisions behind each result.

Our fictional expense-policy demonstration completed this loop: a missed receipt
step led to coaching and fresh evidence; a later policy update carried three
unchanged objectives forward and reassessed the changed receipt rule. A successful
new case restored readiness for the updated procedure.

## The agent's role

1. Read authenticated learner evidence and eligible activities.
2. Select a useful approved activity or choose read tools for a policy question.
3. Return a structured decision, which the backend validates before execution.
4. Use retrieved approved passages for cited explanations.

This is bounded agency. Scoring, source approval, publication and revision activation
remain application or trainer responsibilities. A decision record preserves the
selection, observable evidence and source reference, not private model reasoning.

## What distinguishes the demonstration

- **Beyond document chat:** the workflow ends in demonstrated procedure objectives,
  rather than only an answer to a question.
- **Beyond a course-completion badge:** readiness requires fresh cases and all
  critical objectives, tied to a source version.
- **Targeted refreshers:** a reviewed policy change preserves equivalent evidence
  and assigns practice for affected objectives.
- **Inspectable decisions:** trainers can follow a result back to saved evidence,
  activity selection and source references.

These are product-design distinctions, not claims that no competing product offers
similar capabilities. No external competitor benchmark has been performed.

## Built and verified

- Local FastAPI application, plain JavaScript interface and SQLite persistence.
- Ollama-compatible gateway adapter, typed read tools and bounded JSON repair.
- Optional OpenClaw Chat Completions adapter, with offline protocol/workflow tests;
  real OpenClaw configuration and behavior still need verification.
- Learner diagnostics, coaching, fresh cases and trainer review queue.
- Trainer-approved procedure revisions and evidence carryover.
- Trainer dashboard and isolated live/offline rehearsal creation.
- Current source validation: 193 Python tests and 2 dashboard aggregation tests
  passed on 27 September 2026. These are offline regression checks.
- One authorized Ollama-compatible gateway run passed all three smoke checks:
  eligible activity selection without changing scores, approved-policy citations,
  and referral for an unsupported question.
- The course-generation request in that run timed out at 60 seconds and returned
  503. Course calls now allow 180 seconds, with offline tests; a further paid course
  request has not been authorized or completed. This is not a live generation pass.
- A previous browser rehearsal completed the original and revised fictional
  procedure; [REHEARSAL.md](REHEARSAL.md) records that observation and its limits.

The older deployment package's verification was **71 Python + 2 dashboard tests**.
That historical result must not be replaced with the current source count without
rebuilding and testing the packaged commit. Test counts are not a reliability or
learning-effectiveness measure.

The resumed rehearsal segment took about 2m 47s, but excluded earlier diagnostic
work and an interruption. Do not claim the entire journey was timed under three minutes.

## Limits and next validation

This is a local prototype with fictional content and shared demo accounts. Retrieval
is lexical; citation validation does not prove semantic correctness. Procedure impact
comparison is deterministic and trainer-approved. Broader gateway reliability,
learning retention, trainer effort and time savings have not been measured.

Next, pilot one real procedure with a consenting training team, have a trainer review
all material, and compare fresh-case performance, retained understanding and trainer
review effort against the team's existing process. Public deployment and managed
identity remain separate work.

## Submission assets

- [Verified current deployment ZIP](output/deployment/20260928-pr-v2/AgentX_Learn_Deployment.zip) and [extracted-package verification](output/deployment/20260928-pr-v2/VERIFICATION.md)
- [Pitch and judging questions](PITCH.md)
- [Presentation checklist and offline fallback](DEMO-CHECKLIST.md)
- [Demo setup and full workflow](DEMO.md)
- [Observed rehearsal report](REHEARSAL.md)
- [Silent illustrated backup](backup-demo.gif): reconstruction, not screen capture.
- [Local setup and technical details](README.md)

## Organizer-specific fields still needed

The repository is [KaenBin/AgentX](https://github.com/KaenBin/AgentX), with an existing
`master` branch. The implementation PR URL is pending creation; inclusion in a PR
does not imply review, merge or deployment.

Confirm the team code, submission recipient, track or assigned problem statement,
judging rubric, team/contact details, word limits, video rules, and the organizer's
deadline and time zone. The next team's presentation date is not a verified
submission deadline. No verified public deployment URL or actual screen-recording
URL is supplied here. The final submission email remains a draft.
