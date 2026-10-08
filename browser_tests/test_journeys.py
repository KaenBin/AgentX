"""Learner and trainer journeys through the real demo interface."""

import re

from playwright.sync_api import expect
import pytest


def sign_in(page, name="learner"):
    """Use the login form and wait for the authenticated workspace."""
    page.get_by_label("Username", exact=True).fill(name)
    page.get_by_label("Password", exact=True).fill("LearnDemo2026!")
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_be_visible()


def next_activity(page, start=False):
    """Ask the UI to issue the next saved learning activity."""
    with page.expect_response(lambda response: response.url.endswith("/next") and
                              response.request.method == "POST") as result:
        page.get_by_role("button", name="Start readiness practice" if start else
                         "Coach me through the next step", exact=True).click()
    return result.value.json()["session"]


@pytest.mark.parametrize("mobile", [False, True], ids=["desktop", "mobile"])
def test_login_error_keyboard_sign_in_and_logout(page, mobile):
    """Authentication remains usable at desktop and narrow phone widths."""
    if mobile:
        page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_label("Password", exact=True).fill("incorrect-demo-password")
    page.get_by_label("Password", exact=True).press("Enter")
    expect(page.locator("#notice")).to_have_text("Incorrect username or password")
    page.get_by_label("Password", exact=True).fill("LearnDemo2026!")
    page.get_by_label("Password", exact=True).press("Enter")
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Start readiness practice", exact=True)).to_be_visible()
    assert page.get_by_role("button", name="Trainer studio", exact=True).count() == 0
    if mobile:
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="Sign out", exact=True).click()
    expect(page.get_by_role("button", name="Sign in", exact=True)).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("button", name="Sign in", exact=True)).to_be_visible()


def test_readiness_gap_coaching_resume_and_fresh_cases(page):
    """A missed receipt step needs coaching and fresh evidence before readiness."""
    answers = {
        "What evidence is required for an expense claim?": "Only a bank statement",
        "What is the normal expense submission window?": "30 calendar days after purchase",
        "When must a purchase above SGD 200 receive written manager approval?": "Before the purchase",
        "How long does Finance take to review a complete claim?": "Five business days",
        "Sam has only a card transaction record for a meal expense. Which step satisfies the receipt rule?": "Ask the supplier for a duplicate itemized receipt",
        "Lee finds an unsubmitted claim from 32 calendar days ago. What should happen?": "Refer the late claim for manager review",
        "A work purchase will cost SGD 220. What must happen before the purchase?": "Obtain written manager approval",
        "An expense claim is returned because a required document is missing. Which response follows the policy?": "Correct that claim with the document",
    }
    sign_in(page)
    session = next_activity(page, start=True)
    seen_lesson = False
    resumed = False
    for _ in range(16):
        if session["state"] == "ready":
            break
        if not session["activity"]:
            session = next_activity(page)
        activity = session["activity"]
        form = page.locator("#learning-answer")
        if not resumed:
            expect(form.get_by_role("heading", level=2)).to_have_text(activity["title"])
            page.reload(wait_until="networkidle")
            expect(form.get_by_role("heading", level=2)).to_have_text(activity["title"])
            expect(form.locator("legend")).to_have_text(activity["prompt"])
            resumed = True
        if activity["kind"] == "lesson":
            seen_lesson = True
            assert session["state"] != "ready"
            submit = form.get_by_role("button", name="I have reviewed this step", exact=True)
        else:
            expect(form.locator("legend")).to_have_text(activity["prompt"])
            form.get_by_role("radio", name=answers[activity["prompt"]], exact=True).check()
            submit = form.get_by_role("button", name="Submit my answer", exact=True)
        with page.expect_response(lambda response: response.url.endswith("/answer") and
                                  response.request.method == "POST") as result:
            submit.click()
        session = result.value.json()["session"]
    assert resumed and seen_lesson
    assert session["state"] == "ready"
    assert all(objective["demonstrated"] for objective in session["objectives"] if objective["critical"])
    expect(page.get_by_text("You demonstrated the required steps in this procedure version.", exact=False)).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(page.get_by_text("You demonstrated the required steps in this procedure version.", exact=False)).to_be_visible()
    page.get_by_role("button", name="Progress", exact=True).click()
    expect(page.get_by_role("heading", name="Procedure readiness", exact=True)).to_be_visible()
    expect(page.locator("#content").get_by_text(re.compile("Expense procedure readiness.*ready"))).to_be_visible()


def test_trainer_approves_and_publishes_source_for_learner(page):
    """An unpublished fictional source reaches learners only after approval."""
    sign_in(page, "trainer")
    page.get_by_role("button", name="Trainer studio", exact=True).click()
    page.get_by_label("Document title and version", exact=True).fill("Browser demo travel policy v1")
    page.get_by_label("Document text", exact=True).fill(
        "Travel approval\nGet written approval before booking work travel.\n\n"
        "Travel evidence\nKeep itemized receipts and attach them to the claim."
    )
    page.get_by_role("button", name="Save for review", exact=True).click()
    source = page.locator(".card").filter(has=page.get_by_role("heading", name="Browser demo travel policy v1", exact=True))
    expect(source.get_by_text("Pending", exact=True)).to_be_visible()
    source.get_by_role("button", name="Approve source", exact=True).click()
    source.get_by_role("button", name="Create course draft", exact=True).click()
    draft = page.locator(".card").filter(has=page.get_by_role("button", name="Approve and publish", exact=True))
    expect(draft).to_have_count(1)
    page.get_by_role("button", name="Sign out", exact=True).click()
    sign_in(page)
    expect(page.get_by_label("Choose a course", exact=True).locator("option").filter(
        has_text="Browser demo travel policy v1")).to_have_count(0)
    page.get_by_role("button", name="Sign out", exact=True).click()
    sign_in(page, "trainer")
    page.get_by_role("button", name="Trainer studio", exact=True).click()
    expect(draft).to_have_count(1)
    draft.get_by_role("button", name="Approve and publish", exact=True).click()
    expect(draft).to_have_count(0)
    page.get_by_role("button", name="Sign out", exact=True).click()
    sign_in(page)
    options = page.get_by_label("Choose a course", exact=True).locator("option")
    option = options.filter(has_text="Browser demo travel policy v1")
    expect(option).to_have_count(1)
    page.get_by_label("Choose a course", exact=True).select_option(value=option.get_attribute("value"))
    expect(page.get_by_role("button", name="Start diagnostic", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=re.compile("Browser demo travel policy"))).to_be_visible()
