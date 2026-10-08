# Demo browser regression milestone

Continue the approved fictional-data demo delivery plan by adding repeatable browser
coverage to the existing learner and trainer journeys. Preserve current application
architecture and scoring; each browser case runs against a fresh temporary SQLite
database in offline mode with no gateway credentials.

1. Pin browser tooling separately from normal runtime and developer dependencies.
2. Add cross-platform server and Chromium lifecycle fixtures with independent data
   per test, bounded startup waits, and useful failure screenshots and traces.
3. Exercise invalid login, logout, readiness gaps/coaching/fresh-case completion and
   resume, trainer approval/publication, and a mobile learner viewport.
4. Add a browser CI job and retain diagnostic artifacts only when checks fail.
5. Document local execution and source-bundle support. Run all existing checks,
   get independent review, and create a PR toward dev.

Branch: feat/demo-browser-regressions, from merged origin/dev at 402e8be.
Commit each verified milestone locally. Master is production; do not merge.
Human pilot results and customer production controls remain separate work.
