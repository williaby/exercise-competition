"""Unit tests for Strava integration (service layer and API routes)."""

from __future__ import annotations

import datetime
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from exercise_competition.models import (
    Base,
    Participant,
    StravaActivity,
    StravaToken,
    WeeklySubmission,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_session(db_session):
    """Session with 4 participants pre-seeded."""
    for name in [
        "Byron Williams",
        "Justin Williams",
        "Nick Williams",
        "Bruce Williams",
    ]:
        db_session.add(Participant(name=name))
    db_session.commit()
    return db_session


@pytest.fixture
def patched_session(seeded_session):
    """Patch get_session to use the in-memory seeded session."""
    from contextlib import contextmanager

    @contextmanager
    def _fake_session():
        yield seeded_session

    with patch("exercise_competition.services.strava.get_session", _fake_session):
        yield seeded_session


@pytest.fixture
def sample_token_data():
    """Sample Strava token exchange response."""
    return {
        "access_token": "access_abc123",
        "refresh_token": "refresh_xyz789",
        "expires_at": int(time.time()) + 21600,
        "athlete": {"id": 12345678},
        "scope": "activity:read",
    }


@pytest.fixture
def participant_with_token(seeded_session):
    """Create a participant with a Strava token."""
    p = seeded_session.query(Participant).first()
    token = StravaToken(
        participant_id=p.id,
        strava_athlete_id=99999,
        access_token="valid_access",
        refresh_token="valid_refresh",
        expires_at=int(time.time()) + 3600,
        scope="activity:read",
    )
    seeded_session.add(token)
    seeded_session.commit()
    return p, token


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestStravaTokenModel:
    """Tests for the StravaToken model."""

    def test_create_strava_token(self, seeded_session):
        p = seeded_session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=12345,
            access_token="abc",
            refresh_token="xyz",
            expires_at=int(time.time()) + 3600,
        )
        seeded_session.add(token)
        seeded_session.commit()

        result = seeded_session.query(StravaToken).first()
        assert result.participant_id == p.id
        assert result.strava_athlete_id == 12345
        assert result.scope == "activity:read"

    def test_is_expired_false(self, seeded_session):
        p = seeded_session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=12345,
            access_token="abc",
            refresh_token="xyz",
            expires_at=int(time.time()) + 3600,
        )
        seeded_session.add(token)
        seeded_session.commit()
        assert token.is_expired is False

    def test_is_expired_true(self, seeded_session):
        p = seeded_session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=12345,
            access_token="abc",
            refresh_token="xyz",
            expires_at=int(time.time()) - 100,
        )
        seeded_session.add(token)
        seeded_session.commit()
        assert token.is_expired is True

    def test_repr(self, seeded_session):
        p = seeded_session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=12345,
            access_token="abc",
            refresh_token="xyz",
            expires_at=int(time.time()),
        )
        seeded_session.add(token)
        seeded_session.commit()
        r = repr(token)
        assert "StravaToken" in r
        assert "12345" in r


class TestStravaActivityModel:
    """Tests for the StravaActivity model."""

    def test_create_activity(self, seeded_session):
        p = seeded_session.query(Participant).first()
        activity = StravaActivity(
            participant_id=p.id,
            strava_activity_id=987654,
            activity_type="Run",
            name="Morning Run",
            start_date_local=datetime.datetime(
                2026, 4, 1, 8, 0, 0, tzinfo=datetime.timezone.utc
            ),
            elapsed_time_seconds=2400,
            moving_time_seconds=2100,
            distance_meters=5000.0,
        )
        seeded_session.add(activity)
        seeded_session.commit()

        result = seeded_session.query(StravaActivity).first()
        assert result.activity_type == "Run"
        assert result.strava_activity_id == 987654

    def test_duration_minutes(self, seeded_session):
        p = seeded_session.query(Participant).first()
        activity = StravaActivity(
            participant_id=p.id,
            strava_activity_id=111,
            activity_type="Ride",
            name="Ride",
            start_date_local=datetime.datetime(
                2026, 4, 1, 8, 0, 0, tzinfo=datetime.timezone.utc
            ),
            elapsed_time_seconds=3600,
            moving_time_seconds=1800,
        )
        seeded_session.add(activity)
        seeded_session.commit()
        assert activity.duration_minutes == pytest.approx(30.0)

    def test_repr(self, seeded_session):
        p = seeded_session.query(Participant).first()
        activity = StravaActivity(
            participant_id=p.id,
            strava_activity_id=222,
            activity_type="Swim",
            name="Pool",
            start_date_local=datetime.datetime(
                2026, 4, 1, 8, 0, 0, tzinfo=datetime.timezone.utc
            ),
            elapsed_time_seconds=1800,
            moving_time_seconds=1500,
        )
        seeded_session.add(activity)
        seeded_session.commit()
        r = repr(activity)
        assert "StravaActivity" in r
        assert "Swim" in r


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------


class TestGetStravaAuthUrl:
    """Tests for get_strava_auth_url."""

    def test_returns_url_with_encoded_params(self):
        from exercise_competition.services.strava import get_strava_auth_url

        with patch("exercise_competition.services.strava.settings") as mock_settings:
            mock_settings.strava_client_id = "test_client_id"
            mock_settings.strava_redirect_uri = "https://example.com/callback?foo=bar"

            url = get_strava_auth_url(42)

        assert "client_id=test_client_id" in url
        assert "state=42" in url
        assert "response_type=code" in url
        assert "scope=activity%3Aread" in url
        # urlencode should encode the ? and = in the redirect_uri
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback%3Ffoo%3Dbar" in url

    def test_url_starts_with_strava_auth(self):
        from exercise_competition.services.strava import get_strava_auth_url

        with patch("exercise_competition.services.strava.settings") as mock_settings:
            mock_settings.strava_client_id = "123"
            mock_settings.strava_redirect_uri = "https://example.com/cb"

            url = get_strava_auth_url(1)

        assert url.startswith("https://www.strava.com/oauth/authorize?")


class TestExchangeStravaCode:
    """Tests for exchange_strava_code."""

    def test_successful_exchange(self):
        from exercise_competition.services.strava import exchange_strava_code

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 9999999999,
            "athlete": {"id": 1},
        }

        with (
            patch("exercise_competition.services.strava.settings"),
            patch(
                "exercise_competition.services.strava.httpx.Client"
            ) as mock_client_cls,
        ):
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = exchange_strava_code("test_code")

        assert result["access_token"] == "tok"

    def test_exchange_raises_on_http_error(self):
        from exercise_competition.services.strava import exchange_strava_code

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        )

        with (
            patch("exercise_competition.services.strava.settings"),
            patch(
                "exercise_competition.services.strava.httpx.Client"
            ) as mock_client_cls,
        ):
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                exchange_strava_code("bad_code")


class TestSaveStravaToken:
    """Tests for save_strava_token."""

    def test_creates_new_token(self, patched_session, sample_token_data):
        from exercise_competition.services.strava import save_strava_token

        session = patched_session
        p = session.query(Participant).first()
        result = save_strava_token(p.id, sample_token_data)

        assert result.participant_id == p.id
        assert result.strava_athlete_id == 12345678
        assert result.access_token == "access_abc123"

    def test_updates_existing_token(self, patched_session, sample_token_data):
        from exercise_competition.services.strava import save_strava_token

        session = patched_session
        p = session.query(Participant).first()

        # Create first
        save_strava_token(p.id, sample_token_data)

        # Update with new data
        updated_data = {
            **sample_token_data,
            "access_token": "new_access",
            "refresh_token": "new_refresh",
        }
        result = save_strava_token(p.id, updated_data)

        assert result.access_token == "new_access"
        assert result.refresh_token == "new_refresh"

        # Only one token in DB
        tokens = session.query(StravaToken).all()
        assert len(tokens) == 1


class TestRefreshStravaToken:
    """Tests for refresh_strava_token."""

    def test_refresh_updates_db(self, patched_session):
        from exercise_competition.services.strava import refresh_strava_token

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="old_access",
            refresh_token="old_refresh",
            expires_at=int(time.time()) - 100,
        )
        session.add(token)
        session.commit()

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_at": int(time.time()) + 7200,
        }

        with patch(
            "exercise_competition.services.strava.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = refresh_strava_token(token)

        assert result.access_token == "new_access"
        assert result.refresh_token == "new_refresh"

    def test_refresh_returns_fresh_data_when_db_deleted(self, patched_session):
        """When the DB record is deleted between refresh and lookup."""
        from exercise_competition.services.strava import refresh_strava_token

        session = patched_session
        p = session.query(Participant).first()

        # Create a token that won't exist in DB (use a fake id)
        token = StravaToken(
            id=99999,
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="old_access",
            refresh_token="old_refresh",
            expires_at=int(time.time()) - 100,
        )

        new_expires = int(time.time()) + 7200
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "access_token": "fresh_access",
            "refresh_token": "fresh_refresh",
            "expires_at": new_expires,
        }

        with patch(
            "exercise_competition.services.strava.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = refresh_strava_token(token)

        # Should return fresh data, not the stale original
        assert result.access_token == "fresh_access"
        assert result.refresh_token == "fresh_refresh"
        assert result.expires_at == new_expires


class TestGetValidToken:
    """Tests for _get_valid_token."""

    def test_returns_same_token_if_not_expired(self):
        from exercise_competition.services.strava import _get_valid_token

        token = StravaToken(
            id=1,
            participant_id=1,
            strava_athlete_id=1,
            access_token="valid",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        result = _get_valid_token(token)
        assert result is token

    def test_refreshes_if_expired(self):
        from exercise_competition.services.strava import _get_valid_token

        token = StravaToken(
            id=1,
            participant_id=1,
            strava_athlete_id=1,
            access_token="old",
            refresh_token="ref",
            expires_at=int(time.time()) - 100,
        )

        refreshed = StravaToken(
            id=1,
            participant_id=1,
            strava_athlete_id=1,
            access_token="new",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )

        with patch(
            "exercise_competition.services.strava.refresh_strava_token",
            return_value=refreshed,
        ):
            result = _get_valid_token(token)

        assert result.access_token == "new"


class TestFetchStravaActivities:
    """Tests for fetch_strava_activities."""

    def test_fetches_single_page(self):
        from exercise_competition.services.strava import fetch_strava_activities

        token = StravaToken(
            id=1,
            participant_id=1,
            strava_athlete_id=1,
            access_token="tok",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )

        activities = [{"id": i, "name": f"Activity {i}"} for i in range(5)]
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = activities

        with patch(
            "exercise_competition.services.strava.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = fetch_strava_activities(token, after=1000)

        assert len(result) == 5

    def test_fetches_multiple_pages(self):
        from exercise_competition.services.strava import fetch_strava_activities

        token = StravaToken(
            id=1,
            participant_id=1,
            strava_athlete_id=1,
            access_token="tok",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )

        page1 = [{"id": i} for i in range(100)]
        page2 = [{"id": i} for i in range(100, 130)]

        mock_resp1 = MagicMock(spec=httpx.Response)
        mock_resp1.json.return_value = page1
        mock_resp2 = MagicMock(spec=httpx.Response)
        mock_resp2.json.return_value = page2

        with patch(
            "exercise_competition.services.strava.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = [mock_resp1, mock_resp2]
            mock_client_cls.return_value = mock_client

            result = fetch_strava_activities(token)

        assert len(result) == 130


class TestDateHelpers:
    """Tests for _date_to_weekday_field and _date_to_competition_week."""

    def test_weekday_field_monday(self):
        from exercise_competition.services.strava import _date_to_weekday_field

        # 2026-03-30 is a Monday
        dt = datetime.datetime(2026, 3, 30, 10, 0, 0, tzinfo=datetime.timezone.utc)
        assert _date_to_weekday_field(dt) == "monday"

    def test_weekday_field_sunday(self):
        from exercise_competition.services.strava import _date_to_weekday_field

        # 2026-04-05 is a Sunday
        dt = datetime.datetime(2026, 4, 5, 10, 0, 0, tzinfo=datetime.timezone.utc)
        assert _date_to_weekday_field(dt) == "sunday"

    def test_competition_week_first_day(self):
        from exercise_competition.services.strava import _date_to_competition_week

        # Competition starts 2026-03-23
        assert _date_to_competition_week(datetime.date(2026, 3, 23)) == 1

    def test_competition_week_second_week(self):
        from exercise_competition.services.strava import _date_to_competition_week

        assert _date_to_competition_week(datetime.date(2026, 3, 30)) == 2

    def test_competition_week_before_start(self):
        from exercise_competition.services.strava import _date_to_competition_week

        assert _date_to_competition_week(datetime.date(2026, 3, 22)) is None

    def test_competition_week_after_end(self):
        from exercise_competition.services.strava import _date_to_competition_week

        # 20 weeks from 2026-03-23 = 2026-08-10, so 2026-08-11 is week 21
        assert _date_to_competition_week(datetime.date(2026, 8, 11)) is None


class TestUpdateWeeklySubmission:
    """Tests for _update_weekly_submission."""

    def test_creates_new_submission(self, seeded_session):
        from exercise_competition.services.strava import _update_weekly_submission

        p = seeded_session.query(Participant).first()
        _update_weekly_submission(seeded_session, p.id, 1, "monday")
        seeded_session.flush()

        sub = seeded_session.query(WeeklySubmission).first()
        assert sub.monday is True
        assert sub.tuesday is False

    def test_updates_existing_submission(self, seeded_session):
        from exercise_competition.services.strava import _update_weekly_submission

        p = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=p.id,
            week_number=1,
            monday=True,
        )
        seeded_session.add(sub)
        seeded_session.flush()

        _update_weekly_submission(seeded_session, p.id, 1, "wednesday")
        seeded_session.flush()

        result = seeded_session.query(WeeklySubmission).first()
        assert result.monday is True
        assert result.wednesday is True

    def test_never_reverts_true_to_false(self, seeded_session):
        from exercise_competition.services.strava import _update_weekly_submission

        p = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=p.id,
            week_number=1,
            monday=True,
        )
        seeded_session.add(sub)
        seeded_session.flush()

        # Calling with "monday" again should NOT revert it
        _update_weekly_submission(seeded_session, p.id, 1, "monday")
        seeded_session.flush()

        result = seeded_session.query(WeeklySubmission).first()
        assert result.monday is True


class TestGetConnectedParticipants:
    """Tests for get_connected_participants."""

    def test_returns_all_participants_with_status(self, patched_session):
        from exercise_competition.services.strava import get_connected_participants

        session = patched_session
        p = session.query(Participant).first()

        # Connect one participant
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=99999,
            access_token="a",
            refresh_token="r",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        result = get_connected_participants()
        assert len(result) == 4

        connected = [r for r in result if r["strava_connected"]]
        disconnected = [r for r in result if not r["strava_connected"]]
        assert len(connected) == 1
        assert len(disconnected) == 3
        assert connected[0]["strava_athlete_id"] == 99999


class TestDisconnectStrava:
    """Tests for disconnect_strava."""

    def test_disconnect_existing(self, patched_session):
        from exercise_competition.services.strava import disconnect_strava

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=99999,
            access_token="a",
            refresh_token="r",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        with patch(
            "exercise_competition.services.strava.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = disconnect_strava(p.id)

        assert result is True
        assert session.query(StravaToken).count() == 0

    def test_disconnect_nonexistent(self, patched_session):
        from exercise_competition.services.strava import disconnect_strava

        result = disconnect_strava(9999)
        assert result is False

    def test_disconnect_handles_deauth_failure(self, patched_session):
        from exercise_competition.services.strava import disconnect_strava

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=99999,
            access_token="a",
            refresh_token="r",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        with patch(
            "exercise_competition.services.strava.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock(spec=["post", "get", "__enter__", "__exit__"])
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.HTTPError("Connection error")
            mock_client_cls.return_value = mock_client

            result = disconnect_strava(p.id)

        # Should still succeed (deauth is best-effort)
        assert result is True
        assert session.query(StravaToken).count() == 0


class TestSyncParticipantActivities:
    """Tests for sync_participant_activities."""

    def test_raises_if_no_connection(self, patched_session):
        from exercise_competition.services.strava import sync_participant_activities

        with pytest.raises(ValueError, match="No Strava connection"):
            sync_participant_activities(9999)

    def test_syncs_qualifying_activities(self, patched_session):
        from exercise_competition.services.strava import sync_participant_activities

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="valid",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        # Activity on 2026-04-01 (Wednesday, week 1) — 35 min moving time
        activities = [
            {
                "id": 1001,
                "type": "Run",
                "name": "Morning Run",
                "start_date_local": "2026-04-01T08:00:00",
                "elapsed_time": 2400,
                "moving_time": 2100,  # 35 minutes
                "distance": 5000.0,
            }
        ]

        with patch(
            "exercise_competition.services.strava.fetch_strava_activities",
            return_value=activities,
        ):
            count = sync_participant_activities(p.id)

        assert count == 1
        # Check activity was stored
        stored = session.query(StravaActivity).first()
        assert stored.strava_activity_id == 1001

        # Check weekly submission was created
        sub = session.query(WeeklySubmission).first()
        assert sub.wednesday is True

    def test_skips_short_activities(self, patched_session):
        from exercise_competition.services.strava import sync_participant_activities

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="valid",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        # Activity only 10 minutes — below threshold
        activities = [
            {
                "id": 2001,
                "type": "Walk",
                "name": "Short Walk",
                "start_date_local": "2026-04-01T08:00:00",
                "elapsed_time": 600,
                "moving_time": 600,
                "distance": 1000.0,
            }
        ]

        with patch(
            "exercise_competition.services.strava.fetch_strava_activities",
            return_value=activities,
        ):
            count = sync_participant_activities(p.id)

        assert count == 1  # activity stored
        # But no weekly submission
        sub = session.query(WeeklySubmission).first()
        assert sub is None

    def test_skips_duplicate_activities(self, patched_session):
        from exercise_competition.services.strava import sync_participant_activities

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="valid",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)

        # Pre-existing activity
        existing = StravaActivity(
            participant_id=p.id,
            strava_activity_id=3001,
            activity_type="Run",
            name="Existing",
            start_date_local=datetime.datetime(
                2026, 4, 1, 8, 0, 0, tzinfo=datetime.timezone.utc
            ),
            elapsed_time_seconds=2400,
            moving_time_seconds=2100,
        )
        session.add(existing)
        session.commit()

        activities = [
            {
                "id": 3001,
                "type": "Run",
                "name": "Existing",
                "start_date_local": "2026-04-01T08:00:00",
                "elapsed_time": 2400,
                "moving_time": 2100,
            }
        ]

        with patch(
            "exercise_competition.services.strava.fetch_strava_activities",
            return_value=activities,
        ):
            count = sync_participant_activities(p.id)

        assert count == 0

    def test_skips_bad_date_activities(self, patched_session):
        from exercise_competition.services.strava import sync_participant_activities

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="valid",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        activities = [
            {
                "id": 4001,
                "type": "Run",
                "name": "Bad Date",
                "start_date_local": "not-a-date",
                "elapsed_time": 2400,
                "moving_time": 2100,
            }
        ]

        with patch(
            "exercise_competition.services.strava.fetch_strava_activities",
            return_value=activities,
        ):
            count = sync_participant_activities(p.id)

        assert count == 0

    def test_skips_activities_outside_competition(self, patched_session):
        from exercise_competition.services.strava import sync_participant_activities

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=11111,
            access_token="valid",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        # Activity before competition start
        activities = [
            {
                "id": 5001,
                "type": "Run",
                "name": "Pre-competition",
                "start_date_local": "2026-03-01T08:00:00",
                "elapsed_time": 2400,
                "moving_time": 2100,
            }
        ]

        with patch(
            "exercise_competition.services.strava.fetch_strava_activities",
            return_value=activities,
        ):
            count = sync_participant_activities(p.id)

        assert count == 0


class TestSyncAllConnectedParticipants:
    """Tests for sync_all_connected_participants."""

    def test_syncs_all_connected(self, patched_session):
        from exercise_competition.services.strava import (
            sync_all_connected_participants,
        )

        session = patched_session
        participants = session.query(Participant).limit(2).all()

        for p in participants:
            token = StravaToken(
                participant_id=p.id,
                strava_athlete_id=p.id * 1000,
                access_token="tok",
                refresh_token="ref",
                expires_at=int(time.time()) + 3600,
            )
            session.add(token)
        session.commit()

        with patch(
            "exercise_competition.services.strava.sync_participant_activities",
            return_value=3,
        ):
            results = sync_all_connected_participants()

        assert len(results) == 2
        for count in results.values():
            assert count == 3

    def test_handles_sync_failure(self, patched_session):
        from exercise_competition.services.strava import (
            sync_all_connected_participants,
        )

        session = patched_session
        p = session.query(Participant).first()
        token = StravaToken(
            participant_id=p.id,
            strava_athlete_id=99999,
            access_token="tok",
            refresh_token="ref",
            expires_at=int(time.time()) + 3600,
        )
        session.add(token)
        session.commit()

        with patch(
            "exercise_competition.services.strava.sync_participant_activities",
            side_effect=RuntimeError("API error"),
        ):
            results = sync_all_connected_participants()

        assert len(results) == 1
        # Failed syncs get -1
        assert next(iter(results.values())) == -1


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestStravaAPIRoutes:
    """Tests for Strava API endpoints via FastAPI TestClient."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from exercise_competition.main import app

        return TestClient(app, follow_redirects=False)

    def test_strava_settings_page(self, client):
        with patch(
            "exercise_competition.api.strava.get_connected_participants",
            return_value=[],
        ):
            resp = client.get("/strava")
        assert resp.status_code == 200

    def test_strava_connect_not_configured(self, client):
        with patch("exercise_competition.api.strava.settings") as mock_settings:
            mock_settings.strava_client_id = ""
            resp = client.get("/strava/connect/1")
        assert resp.status_code == 302
        assert "strava_not_configured" in resp.headers["location"]

    def test_strava_connect_invalid_participant(self, client):
        with (
            patch("exercise_competition.api.strava.settings") as mock_settings,
            patch("exercise_competition.api.strava.get_session") as mock_get_session,
        ):
            mock_settings.strava_client_id = "test_id"
            mock_session = MagicMock(spec=["__enter__", "__exit__", "get"])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = None
            mock_get_session.return_value = mock_session

            resp = client.get("/strava/connect/9999")
        assert resp.status_code == 302
        assert "invalid_participant" in resp.headers["location"]

    def test_strava_connect_success(self, client):
        mock_participant = MagicMock(spec=Participant)

        with (
            patch("exercise_competition.api.strava.settings") as mock_settings,
            patch("exercise_competition.api.strava.get_session") as mock_get_session,
            patch(
                "exercise_competition.api.strava.get_strava_auth_url",
                return_value="https://strava.com/oauth?test=1",
            ),
        ):
            mock_settings.strava_client_id = "test_id"
            mock_session = MagicMock(spec=["__enter__", "__exit__", "get"])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_participant
            mock_get_session.return_value = mock_session

            resp = client.get("/strava/connect/1")
        assert resp.status_code == 302
        assert "strava.com" in resp.headers["location"]

    def test_strava_callback_error(self, client):
        resp = client.get("/strava/callback?error=access_denied")
        assert resp.status_code == 302
        assert "auth_denied" in resp.headers["location"]

    def test_strava_callback_missing_params(self, client):
        resp = client.get("/strava/callback")
        assert resp.status_code == 302
        assert "auth_error" in resp.headers["location"]

    def test_strava_callback_invalid_state(self, client):
        resp = client.get("/strava/callback?code=abc&state=notanint")
        assert resp.status_code == 302
        assert "auth_error" in resp.headers["location"]

    def test_strava_callback_invalid_participant(self, client):
        with patch("exercise_competition.api.strava.get_session") as mock_get_session:
            mock_session = MagicMock(spec=["__enter__", "__exit__", "get"])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = None
            mock_get_session.return_value = mock_session

            resp = client.get("/strava/callback?code=abc&state=999")
        assert resp.status_code == 302
        assert "invalid_participant" in resp.headers["location"]

    def test_strava_callback_success(self, client):
        mock_participant = MagicMock(spec=Participant)

        with (
            patch("exercise_competition.api.strava.get_session") as mock_get_session,
            patch(
                "exercise_competition.api.strava.exchange_strava_code",
                return_value={
                    "access_token": "t",
                    "refresh_token": "r",
                    "expires_at": 9999,
                    "athlete": {"id": 1},
                },
            ),
            patch("exercise_competition.api.strava.save_strava_token"),
            patch(
                "exercise_competition.api.strava.sync_participant_activities",
                return_value=5,
            ),
        ):
            mock_session = MagicMock(spec=["__enter__", "__exit__", "get"])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_participant
            mock_get_session.return_value = mock_session

            resp = client.get("/strava/callback?code=valid_code&state=1")
        assert resp.status_code == 302
        assert "connected" in resp.headers["location"]

    def test_strava_callback_exchange_failure(self, client):
        mock_participant = MagicMock(spec=Participant)

        with (
            patch("exercise_competition.api.strava.get_session") as mock_get_session,
            patch(
                "exercise_competition.api.strava.exchange_strava_code",
                side_effect=RuntimeError("exchange failed"),
            ),
        ):
            mock_session = MagicMock(spec=["__enter__", "__exit__", "get"])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_participant
            mock_get_session.return_value = mock_session

            resp = client.get("/strava/callback?code=bad&state=1")
        assert resp.status_code == 302
        assert "auth_error" in resp.headers["location"]

    def test_strava_callback_sync_failure_still_connects(self, client):
        mock_participant = MagicMock(spec=Participant)

        with (
            patch("exercise_competition.api.strava.get_session") as mock_get_session,
            patch(
                "exercise_competition.api.strava.exchange_strava_code",
                return_value={
                    "access_token": "t",
                    "refresh_token": "r",
                    "expires_at": 9999,
                    "athlete": {"id": 1},
                },
            ),
            patch("exercise_competition.api.strava.save_strava_token"),
            patch(
                "exercise_competition.api.strava.sync_participant_activities",
                side_effect=RuntimeError("sync failed"),
            ),
        ):
            mock_session = MagicMock(spec=["__enter__", "__exit__", "get"])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_participant
            mock_get_session.return_value = mock_session

            resp = client.get("/strava/callback?code=ok&state=1")
        assert resp.status_code == 302
        assert "connected" in resp.headers["location"]

    def test_disconnect(self, client):
        with patch(
            "exercise_competition.api.strava.disconnect_strava",
            return_value=True,
        ):
            resp = client.post("/strava/disconnect/1")
        assert resp.status_code == 303
        assert "disconnected" in resp.headers["location"]

    def test_disconnect_not_connected(self, client):
        with patch(
            "exercise_competition.api.strava.disconnect_strava",
            return_value=False,
        ):
            resp = client.post("/strava/disconnect/1")
        assert resp.status_code == 303
        assert "not_connected" in resp.headers["location"]

    def test_sync_all(self, client):
        with patch(
            "exercise_competition.api.strava.sync_all_connected_participants",
            return_value={"Byron": 3, "Nick": 2},
        ):
            resp = client.post("/strava/sync")
        assert resp.status_code == 303
        assert "synced_5" in resp.headers["location"]

    def test_sync_all_error(self, client):
        with patch(
            "exercise_competition.api.strava.sync_all_connected_participants",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.post("/strava/sync")
        assert resp.status_code == 303
        assert "sync_error" in resp.headers["location"]

    def test_sync_one(self, client):
        with patch(
            "exercise_competition.api.strava.sync_participant_activities",
            return_value=7,
        ):
            resp = client.post("/strava/sync/1")
        assert resp.status_code == 303
        assert "synced_7" in resp.headers["location"]

    def test_sync_one_not_connected(self, client):
        with patch(
            "exercise_competition.api.strava.sync_participant_activities",
            side_effect=ValueError("not connected"),
        ):
            resp = client.post("/strava/sync/1")
        assert resp.status_code == 303
        assert "not_connected" in resp.headers["location"]

    def test_sync_one_error(self, client):
        with patch(
            "exercise_competition.api.strava.sync_participant_activities",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.post("/strava/sync/1")
        assert resp.status_code == 303
        assert "sync_error" in resp.headers["location"]

    def test_webhook_verify_valid(self, client):
        with patch("exercise_competition.api.strava.settings") as mock_settings:
            mock_settings.strava_webhook_verify_token = "my_secret"
            resp = client.get(
                "/strava/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.challenge": "challenge_abc",
                    "hub.verify_token": "my_secret",
                },
            )
        assert resp.status_code == 200
        assert resp.json() == {"hub.challenge": "challenge_abc"}

    def test_webhook_verify_invalid_mode(self, client):
        resp = client.get(
            "/strava/webhook",
            params={"hub.mode": "wrong"},
        )
        assert resp.status_code == 400

    def test_webhook_verify_invalid_token(self, client):
        with patch("exercise_competition.api.strava.settings") as mock_settings:
            mock_settings.strava_webhook_verify_token = "correct"
            resp = client.get(
                "/strava/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.challenge": "x",
                    "hub.verify_token": "wrong",
                },
            )
        assert resp.status_code == 403

    def test_webhook_event_post(self, client):
        resp = client.post("/strava/webhook")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
