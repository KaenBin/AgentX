# Deployment artifact verification

Verified: 2026-09-27T01:00:47.063982+00:00

Artifact: AgentX_Learn_Deployment.zip

SHA-256: 7b5e967ebd007eade976bcdbb1ef7cfdd88d9206061a50ba67da780ce2fb770d

All payload hashes matched after extraction. Tests on the extracted code: **71 Python tests passed** (two dependency deprecation warnings) and **2 dashboard tests passed**.

The extracted application started on localhost:8015 in demo mode. Health returned status ok; fictional learner login succeeded; the original readiness course was present with zero learning sessions.

This is local deployment evidence, not a public endpoint. The installed dependency runtime was reused; a clean dependency download/install was not tested. No gateway calls were made for this verification. Confirm organizer acceptance of a local deployment artifact.
