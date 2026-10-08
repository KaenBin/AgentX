# Deployable demo foundation

Approved scope: a fictional-data demo; customer production readiness remains a later milestone.

1. Separate runtime and development dependencies, pin versions, and document updates.
2. Package the existing application in a non-root container with persistent SQLite data, a health check, and an explicit demo label.
3. Add CI coverage for Python, dashboard JavaScript, and container startup and persistence.
4. Document installation, backup, restore, updates, and release limitations.
5. Verify the complete change, obtain independent review, push the feature branch, and open a PR against master. Never merge without the owner's permission.

Work on `feat/deployable-demo-foundation`, created from `dev`. Preserve existing uncommitted pilot documents. Commit each verified milestone locally.

Acceptance: a fresh checkout can build and start the container without model credentials; health is reachable; stored training state survives container replacement; runtime runs without root privileges; the existing test suite passes. Deployment defaults to localhost and explicitly identifies demo mode. Secrets, local databases, and unrelated files are excluded from the image.
