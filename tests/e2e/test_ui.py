"""Playwright E2E tests for the exercise competition web UI.

Tests the full user journey: navigation, form submission, leaderboard,
and week detail views in a real browser against a real server.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

PARTICIPANTS = ["Bruce Williams", "Byron Williams", "Justin Williams", "Nick Williams"]


def _goto(page: Page, url: str) -> None:
    """Navigate to a URL and wait for the page to be fully loaded."""
    response = page.goto(url)
    assert response is not None
    assert response.ok, f"Server returned {response.status} for {url}"
    page.wait_for_load_state("domcontentloaded")


# ===========================================================================
# Navigation
# ===========================================================================


class TestNavigation:
    """Test site navigation and page structure."""

    def test_root_redirects_to_leaderboard(self, page: Page, base_url: str) -> None:
        _goto(page, base_url)
        expect(page).to_have_url(re.compile(r"/leaderboard"))

    def test_nav_links_present(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        nav = page.locator("nav")
        expect(nav.get_by_role("link", name="Leaderboard")).to_be_visible()
        expect(nav.get_by_role("link", name="Submit")).to_be_visible()

    def test_nav_to_submit(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        page.get_by_role("link", name="Submit").click()
        expect(page).to_have_url(re.compile(r"/submit"))

    def test_nav_to_leaderboard(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        page.get_by_role("link", name="Leaderboard").click()
        expect(page).to_have_url(re.compile(r"/leaderboard"))


# ===========================================================================
# Submit Form
# ===========================================================================


class TestSubmitForm:
    """Test the exercise submission form."""

    def test_form_renders(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        expect(page.locator("h1")).to_have_text("Log Your Exercise")
        expect(page.locator("form")).to_be_visible()

    def test_participant_dropdown_populated(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        options = page.locator("#participant_name option").all_text_contents()
        for name in PARTICIPANTS:
            assert name in options

    def test_week_dropdown_has_20_weeks(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        options = page.locator("#week_number option")
        expect(options).to_have_count(20)

    def test_seven_day_checkboxes(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        checkboxes = page.locator(".checkbox-grid input[type='checkbox']")
        expect(checkboxes).to_have_count(7)

    def test_checkboxes_are_toggleable(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        monday = page.locator("input[name='monday']")
        expect(monday).not_to_be_checked()
        monday.check()
        expect(monday).to_be_checked()
        monday.uncheck()
        expect(monday).not_to_be_checked()

    def test_submit_button_exists(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        expect(page.get_by_role("button", name="Submit")).to_be_visible()

    def test_csrf_token_present(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")
        csrf = page.locator("input[name='csrf_token']")
        expect(csrf).to_be_hidden()
        value = csrf.get_attribute("value")
        assert value is not None
        assert ":" in value


# ===========================================================================
# Submission E2E Flow
# ===========================================================================


class TestSubmissionFlow:
    """Test the full submit → redirect → leaderboard flow."""

    def test_successful_submission(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")

        page.select_option("#participant_name", "Byron Williams")
        page.select_option("#week_number", "1")
        page.locator("input[name='monday']").check()
        page.locator("input[name='wednesday']").check()
        page.locator("input[name='friday']").check()
        page.get_by_role("button", name="Submit").click()

        # Should redirect to leaderboard with success message
        expect(page).to_have_url(re.compile(r"/leaderboard"))
        expect(page.locator(".alert-success")).to_have_text("Submission recorded!")

    def test_leaderboard_reflects_submission(self, page: Page, base_url: str) -> None:
        """After the submission above, Byron should have 1 point."""
        _goto(page, f"{base_url}/leaderboard")
        # Find Byron's row in the table
        rows = page.locator("tbody tr")
        byron_row = rows.filter(has_text="Byron Williams")
        cells = byron_row.locator("td").all_text_contents()
        # cells: [Rank, Name, Points, Avg Days/Wk, Streak]
        assert "Byron Williams" in cells[1]
        # Byron exercised 3 days (>= 2) so gets 1 point
        assert cells[2] == "1"

    def test_duplicate_submission_shows_error(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")

        page.select_option("#participant_name", "Byron Williams")
        page.select_option("#week_number", "1")
        page.get_by_role("button", name="Submit").click()

        # Should stay on submit page with error
        expect(page).to_have_url(re.compile(r"/submit"))
        expect(page.locator(".alert-error")).to_contain_text(
            "already submitted for week 1"
        )

    def test_submit_second_participant(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/submit")

        page.select_option("#participant_name", "Justin Williams")
        page.select_option("#week_number", "1")
        page.locator("input[name='tuesday']").check()
        page.get_by_role("button", name="Submit").click()

        expect(page).to_have_url(re.compile(r"/leaderboard"))
        expect(page.locator(".alert-success")).to_be_visible()


# ===========================================================================
# Leaderboard
# ===========================================================================


class TestLeaderboard:
    """Test the leaderboard page."""

    def test_leaderboard_renders(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        expect(page.locator("h1")).to_have_text("Leaderboard")
        expect(page.locator("table")).to_be_visible()

    def test_all_participants_listed(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        rows = page.locator("tbody tr")
        expect(rows).to_have_count(4)
        text = page.locator("tbody").text_content()
        for name in PARTICIPANTS:
            assert name in text

    def test_standings_table_headers(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        headers = page.locator("thead th").all_text_contents()
        assert "Rank" in headers
        assert "Name" in headers
        assert "Points" in headers
        assert "Avg Days/Wk" in headers
        assert "Streak" in headers

    def test_week_links_present(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        week_links = page.locator(".week-links a.week-link")
        expect(week_links).to_have_count(20)

    def test_week_link_navigates(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/leaderboard")
        page.locator(".week-links a.week-link").first.click()
        expect(page).to_have_url(re.compile(r"/week/1"))


# ===========================================================================
# Week Detail View
# ===========================================================================


class TestWeekView:
    """Test the week detail page."""

    def test_week_page_renders(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/week/1")
        expect(page.locator("h1")).to_have_text("Week 1 Results")
        expect(page.locator("table")).to_be_visible()

    def test_week_shows_all_participants(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/week/1")
        rows = page.locator("tbody tr")
        expect(rows).to_have_count(4)

    def test_week_shows_submission_checkmarks(self, page: Page, base_url: str) -> None:
        """Byron submitted Mon/Wed/Fri for week 1 in the submission flow tests."""
        _goto(page, f"{base_url}/week/1")
        byron_row = page.locator("tbody tr").filter(has_text="Byron Williams")
        cells = byron_row.locator("td").all_text_contents()
        # cells: [Name, Mon, Tue, Wed, Thu, Fri, Sat, Sun, Days, Status]
        assert "\u2713" in cells[1]  # Mon check
        assert cells[2] == ""  # Tue empty
        assert "\u2713" in cells[3]  # Wed check
        assert cells[4] == ""  # Thu empty
        assert "\u2713" in cells[5]  # Fri check
        assert cells[8] == "3"  # Days count

    def test_week_compliance_badge(self, page: Page, base_url: str) -> None:
        """Byron (3 days) should show Pass; Justin (1 day) should show Miss."""
        _goto(page, f"{base_url}/week/1")

        byron_row = page.locator("tbody tr").filter(has_text="Byron Williams")
        expect(byron_row.locator(".badge-compliant")).to_have_text("Pass")

        justin_row = page.locator("tbody tr").filter(has_text="Justin Williams")
        expect(justin_row.locator(".badge-noncompliant")).to_have_text("Miss")

    def test_no_submission_badge(self, page: Page, base_url: str) -> None:
        """Participants with no submission should show '-' badge."""
        _goto(page, f"{base_url}/week/1")
        nick_row = page.locator("tbody tr").filter(has_text="Nick Williams")
        expect(nick_row.locator(".badge-none")).to_have_text("-")

    def test_back_to_leaderboard_link(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/week/1")
        page.get_by_role("link", name="Back to Leaderboard").click()
        expect(page).to_have_url(re.compile(r"/leaderboard"))

    def test_empty_week_shows_no_submissions(self, page: Page, base_url: str) -> None:
        _goto(page, f"{base_url}/week/20")
        rows = page.locator("tbody tr")
        expect(rows).to_have_count(4)
        # All should show '-' badge (no submissions)
        badges = page.locator(".badge-none")
        expect(badges).to_have_count(4)


# ===========================================================================
# Responsive Layout
# ===========================================================================


@pytest.mark.slow
class TestResponsive:
    """Test mobile responsive layout."""

    def test_mobile_viewport_renders(self, page: Page, base_url: str) -> None:
        page.set_viewport_size({"width": 375, "height": 812})
        _goto(page, f"{base_url}/leaderboard")
        expect(page.locator("h1")).to_be_visible()
        expect(page.locator("table")).to_be_visible()

    def test_mobile_submit_form_usable(self, page: Page, base_url: str) -> None:
        page.set_viewport_size({"width": 375, "height": 812})
        _goto(page, f"{base_url}/submit")
        expect(page.locator("#participant_name")).to_be_visible()
        expect(page.get_by_role("button", name="Submit")).to_be_visible()
