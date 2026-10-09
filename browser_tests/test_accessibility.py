"""Keyboard, announcement, contrast and narrow-navigation regressions."""

import re

from playwright.sync_api import expect
import pytest


def sign_in(page, name="learner"):
    """Submit the real demo login form using the keyboard."""
    page.get_by_label("Username", exact=True).fill(name)
    page.get_by_label("Password", exact=True).press("Enter")
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_be_visible()


def contrast(first, second):
    """Compute relative luminance from the browser's opaque RGB colors."""
    def luminance(color):
        """Linearize sRGB components using the accessibility contrast formula."""
        values = [int(value) / 255 for value in re.findall(r"\d+", color)[:3]]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                  for value in values]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def test_login_error_has_an_announcement_role(page):
    """A rejected login must expose its visible error as an accessible alert."""
    page.get_by_label("Password", exact=True).fill("incorrect-demo-password")
    page.get_by_label("Password", exact=True).press("Enter")
    expect(page.get_by_role("alert")).to_have_text("Incorrect username or password")
    expect(page.get_by_label("Password", exact=True)).to_be_focused()


def test_keyboard_navigation_and_logout_keep_a_logical_focus_target(page):
    """Replacing a workspace view must not drop keyboard focus to the page body."""
    sign_in(page)
    expect(page.locator("#main > h1")).to_be_focused()
    navigation = page.get_by_role("navigation", name="Workspace", exact=True)
    expect(navigation.get_by_role("button", name="Learning path", exact=True)).to_have_attribute("aria-current", "page")
    page.keyboard.press("Tab")
    expect(navigation.get_by_role("button", name="Learning path", exact=True)).to_be_focused()
    navigation.get_by_role("button", name="Progress", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("heading", name="Your course quiz attempts", exact=True)).to_be_focused()
    expect(navigation.get_by_role("button", name="Progress", exact=True)).to_have_attribute("aria-current", "page")
    page.get_by_role("button", name="Sign out", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_label("Username", exact=True)).to_be_focused()
    expect(page.get_by_role("status", name="Workspace updates", exact=True)).to_have_text("Signed out.")


def test_learning_activity_and_saved_answer_restore_keyboard_focus(page):
    """A new activity and its saved result remain reachable without restarting Tab."""
    sign_in(page)
    page.get_by_role("button", name="Start readiness practice", exact=True).focus()
    page.keyboard.press("Enter")
    activity = page.locator("#learning-answer")
    expect(activity.get_by_role("heading", name="Receipt evidence", exact=True)).to_be_focused()
    page.keyboard.press("Tab")
    answer = activity.get_by_role("radio", name="An itemized receipt", exact=True)
    expect(answer).to_be_focused()
    page.keyboard.press("Space")
    activity.get_by_role("button", name="Submit my answer", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Coach me through the next step", exact=True)).to_be_focused()
    expect(page.get_by_role("status", name="Workspace updates", exact=True)).to_contain_text("Correct.")
    assert page.evaluate("document.activeElement !== document.body")
    page.get_by_label("Question or uncertain policy detail", exact=True).fill("Which receipt details should I confirm?")
    page.get_by_role("button", name="Save review request", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_label("Question or uncertain policy detail", exact=True)).to_be_focused()
    expect(page.get_by_role("status", name="Workspace updates", exact=True)).to_have_text("Review request saved for your trainer.")
    expect(page.locator("#selection-reason")).to_have_text("Review request saved for your trainer.")


def test_request_completion_preserves_focus_moved_by_the_user(page):
    """An activity arriving after the user moves focus must not pull them back."""
    sign_in(page)

    def finish_after_focus_moves(route):
        """Move to a surviving control while the next-activity request is pending."""
        page.get_by_role("button", name="Sign out", exact=True).focus()
        route.continue_()

    page.route("**/api/learning/*/next", finish_after_focus_moves)
    page.get_by_role("button", name="Start readiness practice", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.locator("#learning-answer")).to_be_visible()
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_be_focused()


def test_failed_activity_request_keeps_the_retry_button_focused(page):
    """A failed request must announce its error and keep the retry action reachable."""
    sign_in(page)
    page.route("**/api/learning/*/next", lambda route: route.fulfill(
        status=503, json={"error": "Temporary demo failure"}))
    retry = page.get_by_role("button", name="Start readiness practice", exact=True)
    retry.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("alert")).to_have_text("Temporary demo failure")
    expect(retry).to_be_enabled()
    expect(retry).to_be_focused()
    expect(page.get_by_role("status", name="Workspace updates", exact=True)).to_be_empty()


def test_changing_courses_keeps_the_selector_focused(page):
    """Choosing another published course keeps keyboard position after rendering."""
    sign_in(page)
    selector = page.get_by_label("Choose a course", exact=True)
    initial = selector.input_value()
    choices = selector.locator("option").evaluate_all("options => options.map(o => o.value)")
    selector.focus()
    selector.select_option(next(value for value in choices if value != initial))
    expect(selector).to_be_focused()
    selector.select_option(initial)
    expect(selector).to_be_focused()


@pytest.mark.parametrize("name", ["learner", "trainer"])
def test_all_navigation_actions_fit_a_320_pixel_viewport(page, name):
    """The last workspace action must not be clipped inside an unmarked scroll strip."""
    page.set_viewport_size({"width": 320, "height": 844})
    sign_in(page, name)
    actions = page.locator(".tabs button")
    for action in actions.all():
        expect(action).to_be_in_viewport(ratio=1)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_secondary_copy_and_input_focus_have_readable_contrast(page):
    """Rendered text and keyboard focus must remain distinguishable on white cards."""
    muted = page.locator(".card .muted").first
    text = muted.evaluate("e => ({color:getComputedStyle(e).color,background:getComputedStyle(e.closest('.card')).backgroundColor})")
    assert contrast(text["color"], text["background"]) >= 4.5
    field = page.get_by_label("Username", exact=True)
    field.focus()
    focus = field.evaluate("e => ({color:getComputedStyle(e).outlineColor,background:getComputedStyle(e).backgroundColor,width:getComputedStyle(e).outlineWidth})")
    assert float(focus["width"].replace("px", "")) >= 2
    assert contrast(focus["color"], focus["background"]) >= 3
