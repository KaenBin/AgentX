# Demo keyboard and mobile review

This focused review uses fictional seeded content on the demo branch. It covers
login, learning navigation, an issued receipt activity, its saved answer and the
trainer studio at 1280 and 320 CSS pixels. It preserves the existing interface.

## Confirmed gaps and changes

| Observation before the change | Resulting behavior |
| --- | --- |
| Replacing a view leaves keyboard focus on the document body | Sign-in focuses the workspace heading; navigation focuses the destination heading; new activities focus their heading; a saved answer focuses the next-step action |
| Logout removes the focused control | The username field receives focus after sign-out |
| Login and request errors have no announcement role | The visible error container exposes an alert |
| Learning feedback is inserted into a newly created status element | A persistent polite status region receives activity selection, answer feedback and saved review confirmations |
| Secondary copy is `#707d72`: 4.32:1 against white | Secondary copy uses `#526451`: 6.36:1 against white |
| Input and button focus colors are 2.40:1 and 2.50:1 against white | Both use `#285646`: 8.37:1 against white, with visible outlines and spacing |
| At 320 pixels, Progress and Trainer studio are clipped inside the navigation strip | Navigation wraps so every workspace action is visible |

The workspace navigation has an accessible name and identifies its current page.
In the reviewed readiness flow, request completion restores lost focus only; it
preserves focus moved to another surviving control while the request is pending.
Failed activity requests keep the retry action reachable. Choosing a course
restores focus to the replacement selector in both course interfaces. Chat retains
its existing composer-focus behavior and is outside this focus-preservation claim.

The sampled forms already had labels, and the sampled pages did not overflow the
viewport. Wide results tables retain their own scroll container.

## Regression checks

Run the backend and Chromium checks with the project virtual environment:

```sh
python -m pytest tests browser_tests -q
node --test tests/dashboard.test.cjs
```

[Browser testing](BROWSER-TESTING.md) describes isolation and failure evidence.
The accessibility cases check real keyboard actions, accessible roles, computed
contrast, focus after rendering, request retry and a 320-pixel viewport for both
roles. The original learner and trainer journey checks remain in place.

The initial six new cases failed before the UI changes, demonstrating the missing
behavior. Local screenshots and computed observations are generated under
`output/accessibility/`; they are excluded from the source bundle.

Local validation on 9 October 2026: 109 backend and 13 Chromium cases passed,
as did both Node dashboard tests and dependency consistency checks. The Python
suite retains the existing Starlette/httpx deprecation warning. Desktop activity
and mobile trainer screenshots were visually inspected; sampled login, learning,
activity and trainer pages retained their viewport width and labeled fields.

The contrast thresholds used by these checks are informed by W3C guidance on
[text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
The announcement and layout review also uses the explanations for
[status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
and [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).
These targeted checks do not establish full WCAG conformance.

## Human checks still needed

During the owner-arranged volunteer/trainer pilot, observe keyboard-only login,
view changes, wrong and correct answers, request errors, course changes and
sign-out. Confirm visible focus and understandable next steps. Separately check
actual announcements with a screen reader, browser zoom, forced colors and
Safari/Firefox. Test touch and landscape layouts on physical devices.

Chromium viewport emulation and accessible-role assertions do not prove spoken
announcements or usability for people using assistive technology. No human pilot
results, physical-device results or production accessibility sign-off have been
collected here. Record those observations using the
[facilitator sheet](PILOT-FACILITATOR-RUN-SHEET.md) and submit any fixes through a
feature PR to `dev`.
