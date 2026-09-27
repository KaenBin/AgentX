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
- Configured Ollama-compatible gateway adapter, typed read tools, bounded JSON repair.
- Learner diagnostics, coaching, fresh cases and trainer review queue.
- Trainer-approved procedure revisions and evidence carryover.
- Trainer dashboard and isolated live/offline rehearsal creation.
- Latest checks: 71 Python tests and 2 dashboard aggregation tests passed.
- Three consecutive live gateway smoke checks passed after format recovery changes.
- Browser rehearsal completed the original and revised fictional procedure.

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

- [Pitch and judging questions](PITCH.md)
- [Demo setup and full workflow](DEMO.md)
- [Observed rehearsal report](REHEARSAL.md)
- [Silent illustrated backup](backup-demo.gif): reconstruction, not screen capture.
- [Local setup and technical details](README.md)

## Organizer-specific fields still needed

Hackathon name and track, judging rubric, team names, required word limits, repository
URL, permitted demo format and submission deadline. No public URL or actual screen
recording has been produced. This package has not been submitted or published.
