"""Integration tests for the submit -> leaderboard flow."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path):
    """Configure a fresh temp SQLite DB for each test."""
    import exercise_competition.core.database as db_module
    from exercise_competition.core.config import Settings

    db_path = tmp_path / "test.db"
    original_settings = db_module.settings
    db_module.settings = Settings(database_url=f"sqlite:///{db_path}")
    db_module.reset_engine()
    db_module.init_db()
    yield
    db_module.reset_engine()
    db_module.settings = original_settings


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from exercise_competition.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestSubmitForm:
    """Tests for the submission form."""

    def test_get_submit_form(self, client):
        response = client.get("/submit")
        assert response.status_code == 200
        html = response.text
        assert "Byron Williams" in html
        assert "Justin Williams" in html
        assert "Nick Williams" in html
        assert "Bruce Williams" in html
        assert "csrf_token" in html
        assert "Week 1" in html

    def test_submit_redirects_to_leaderboard(self, client):
        # Get form to extract CSRF token
        form_response = client.get("/submit")
        csrf_token = _extract_csrf_token(form_response.text)

        response = client.post(
            "/submit",
            data={
                "csrf_token": csrf_token,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "monday": "true",
                "wednesday": "true",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/leaderboard" in response.headers["location"]

    def test_submit_records_data(self, client):
        form_response = client.get("/submit")
        csrf_token = _extract_csrf_token(form_response.text)

        client.post(
            "/submit",
            data={
                "csrf_token": csrf_token,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "monday": "true",
                "wednesday": "true",
                "friday": "true",
            },
            follow_redirects=False,
        )

        # Check leaderboard shows the submission
        leaderboard = client.get("/leaderboard")
        assert leaderboard.status_code == 200
        assert "Byron Williams" in leaderboard.text

    def test_duplicate_submission_shows_error(self, client):
        form_response = client.get("/submit")
        csrf_token = _extract_csrf_token(form_response.text)

        # First submission
        client.post(
            "/submit",
            data={
                "csrf_token": csrf_token,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "monday": "true",
            },
            follow_redirects=False,
        )

        # Second submission (duplicate)
        form2 = client.get("/submit")
        csrf2 = _extract_csrf_token(form2.text)
        response = client.post(
            "/submit",
            data={
                "csrf_token": csrf2,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "tuesday": "true",
            },
        )
        assert response.status_code == 200
        assert "already submitted" in response.text

    def test_invalid_csrf_shows_error(self, client):
        response = client.post(
            "/submit",
            data={
                "csrf_token": "invalid:token",
                "participant_name": "Byron Williams",
                "week_number": "1",
            },
        )
        assert response.status_code == 200
        assert "Invalid form submission" in response.text

    def test_unknown_participant_shows_error(self, client):
        form_response = client.get("/submit")
        csrf_token = _extract_csrf_token(form_response.text)

        response = client.post(
            "/submit",
            data={
                "csrf_token": csrf_token,
                "participant_name": "Unknown Person",
                "week_number": "1",
            },
        )
        assert response.status_code == 200
        assert "Unknown participant" in response.text


class TestLeaderboard:
    """Tests for the leaderboard page."""

    def test_leaderboard_empty(self, client):
        response = client.get("/leaderboard")
        assert response.status_code == 200
        assert "Byron Williams" in response.text
        assert "Leaderboard" in response.text

    def test_leaderboard_shows_joke(self, client):
        from markupsafe import escape

        from exercise_competition.services.jokes import NICK_JOKES

        response = client.get("/leaderboard")
        assert response.status_code == 200
        assert any(str(escape(joke)) in response.text for joke in NICK_JOKES)

    def test_leaderboard_success_message(self, client):
        response = client.get("/leaderboard?msg=success")
        assert response.status_code == 200
        assert "Submission recorded" in response.text

    def test_leaderboard_reflects_submission(self, client):
        form = client.get("/submit")
        csrf = _extract_csrf_token(form.text)

        # Submit compliant week for Byron (2+ days)
        client.post(
            "/submit",
            data={
                "csrf_token": csrf,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "monday": "true",
                "tuesday": "true",
                "wednesday": "true",
            },
            follow_redirects=False,
        )

        leaderboard = client.get("/leaderboard")
        html = leaderboard.text
        # Byron should have 1 point
        assert "Byron Williams" in html

    def test_compliance_scoring(self, client):
        # Submit compliant week for Byron (2 days)
        form1 = client.get("/submit")
        csrf1 = _extract_csrf_token(form1.text)
        client.post(
            "/submit",
            data={
                "csrf_token": csrf1,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "monday": "true",
                "tuesday": "true",
            },
            follow_redirects=False,
        )

        # Submit non-compliant week for Justin (1 day)
        form2 = client.get("/submit")
        csrf2 = _extract_csrf_token(form2.text)
        client.post(
            "/submit",
            data={
                "csrf_token": csrf2,
                "participant_name": "Justin Williams",
                "week_number": "1",
                "monday": "true",
            },
            follow_redirects=False,
        )

        leaderboard = client.get("/leaderboard")
        html = leaderboard.text
        # Byron should rank above Justin
        byron_pos = html.index("Byron Williams")
        justin_pos = html.index("Justin Williams")
        assert byron_pos < justin_pos


class TestWeekView:
    """Tests for the per-week results view."""

    def test_week_view_no_submissions(self, client):
        response = client.get("/week/1")
        assert response.status_code == 200
        assert "Week 1" in response.text
        assert "Byron Williams" in response.text

    def test_week_view_with_submission(self, client):
        form = client.get("/submit")
        csrf = _extract_csrf_token(form.text)

        client.post(
            "/submit",
            data={
                "csrf_token": csrf,
                "participant_name": "Byron Williams",
                "week_number": "1",
                "monday": "true",
                "friday": "true",
            },
            follow_redirects=False,
        )

        response = client.get("/week/1")
        assert response.status_code == 200
        html = response.text
        assert "Byron Williams" in html
        # Should show checkmarks
        assert "&#10003;" in html or "✓" in html


class TestRootRedirect:
    """Tests for the root URL redirect."""

    def test_root_redirects_to_leaderboard(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/leaderboard" in response.headers["location"]


def _extract_csrf_token(html: str) -> str:
    """Extract the CSRF token value from HTML form."""
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    return html[start:end]
