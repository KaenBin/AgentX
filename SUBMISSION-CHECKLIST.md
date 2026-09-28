# SMYA final submission requirements

Source: organizer announcement screenshot supplied by the user. It does not specify
a deadline, video duration, judging rubric, recipient address or public-hosting rule.

Required subject format shown: **SMYA Final Submission - [confirmed team code]**.
The team's code and recipient still need confirmation. The planned team demonstration
is not evidence of an organizer submission deadline.

| Required item | Current evidence | Status / remaining work |
| --- | --- | --- |
| Team Code | No team-owned code has been verified in this checklist | Confirm before filling the subject and email body |
| Problem Statement | SUBMISSION.md describes version-specific procedure readiness | Draft ready; confirm any organizer-assigned problem statement |
| GitHub Repository URL | [KaenBin/AgentX](https://github.com/KaenBin/AgentX), existing `master` branch | Repository confirmed. Add the implementation PR URL after creation; a PR is not a merged change |
| Business Proposal, PDF | output/pdf/AgentX_Learn_Business_Proposal.pdf | Existing artifact; review its claims and version against the final submission |
| Technical Document, PDF | output/pdf/AgentX_Learn_Technical_Document.pdf | Existing artifact; reconcile technical details and validation counts with the submitted commit |
| Demo Video | backup-demo.gif is an illustrated reconstruction | Actual demo video required: YouTube/cloud URL preferred, or MP4 if practical; GIF does not meet this requirement |
| Deployment Evidence, URL/artifact | [Current verified ZIP](output/deployment/20260928-pr-v2/AgentX_Learn_Deployment.zip), [verification report](output/deployment/20260928-pr-v2/VERIFICATION.md) and adjacent checksum | Extracted current package passed 193 Python and 2 dashboard tests plus offline startup/login checks. The older root-level package remains historical (71 + 2). Confirm acceptance of a local artifact; no public hosting claimed |

## Current source evidence — 27 September 2026

| Check | Actual result | Limit |
| --- | --- | --- |
| Current working source | 193 Python tests and 2 dashboard tests passed | Offline tests include fake transports and loopback HTTP; record the final submitted commit and its own results |
| Authorized Ollama-compatible gateway smoke run | All three checks passed: eligible next activity without score changes, approved-source citations, unsupported-question referral | Three checks in one run, not three independent reliability runs |
| Live course generation | The request timed out at 60 seconds and the route returned 503 | A failure, not a successful generated course; no automatic retry |
| Course timeout fix | Course calls allow 180 seconds; short chat/activity calls remain 60 seconds | Offline-verified change. A further paid course request has not been authorized or completed |
| OpenClaw adapter | Offline protocol, workflow and redirect-protection tests passed | No live OpenClaw instance has been verified |

Use the fixed, reviewed fictional course for the presentation. Follow
[DEMO-CHECKLIST.md](DEMO-CHECKLIST.md); do not depend on generating a new course on stage.

## Completion order

1. Open the implementation PR against `KaenBin/AgentX:master`; add its actual URL to
   the handoff. Keep review/merge status explicit.
2. Confirm team code, recipient, any assigned problem statement, video rules, and
   the actual organizer deadline and time zone.
3. Rehearse the fixed-course sequence, then record the real app and save an MP4.
   Disclose offline mode and prepared evidence; publish only to the agreed destination.
4. Align both PDFs and deployment evidence with the final commit, setup instructions
   and verification output. Confirm
   with organizers whether a local deployment artifact satisfies their expectations.
5. Insert final URLs and filenames into FINAL-EMAIL.md and review all attachments.

Do not include .env, API keys, session cookies, local databases or gateway logs in
the submission package. No email or external publication has been authorized by the
organizer screenshot itself. Sending is a separate user action or explicit request.
