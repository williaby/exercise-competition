"""Strava API integration service.

Handles OAuth token exchange, token refresh, activity fetching, and
auto-population of weekly exercise submissions from Strava data.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, TypedDict, cast
from urllib.parse import urlencode

import httpx

from exercise_competition.core.config import settings
from exercise_competition.core.database import get_session
from exercise_competition.models import (
    Participant,
    StravaActivity,
    StravaToken,
    WeeklySubmission,
)
from exercise_competition.services.cache import standings_cache
from exercise_competition.services.scoring import (
    COMPETITION_START,
    COMPETITION_TZ,
)
from exercise_competition.utils.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"  # noqa: S105  # NOSONAR(S2068) URL constant, not a credential
STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"

# Map day-of-week (0=Monday) to model field names
_WEEKDAY_TO_FIELD = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

_SECONDS_PER_MINUTE = 60


class _StravaAthlete(TypedDict):
    """Strava athlete info from token exchange."""

    id: int


class _StravaTokenExchangeData(TypedDict):
    """Strava OAuth token exchange response."""

    access_token: str
    refresh_token: str
    expires_at: int
    athlete: _StravaAthlete
    scope: str


class _StravaTokenRefreshData(TypedDict):
    """Strava OAuth token refresh response."""

    access_token: str
    refresh_token: str
    expires_at: int


class _StravaActivityData(TypedDict):
    """Strava activity from API response."""

    id: int
    type: str
    name: str
    start_date_local: str
    moving_time: int
    elapsed_time: int
    distance: float | None


class _ParticipantConnection(TypedDict):
    """Participant Strava connection status."""

    id: int
    name: str
    strava_connected: bool
    strava_athlete_id: int | None


def get_strava_auth_url(participant_id: int) -> str:
    """Build the Strava OAuth authorization URL.

    Args:
        participant_id: ID of the participant initiating the connection.
            Passed as the ``state`` parameter for CSRF-like validation.

    Returns:
        Full Strava OAuth authorization URL.
    """
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": settings.strava_redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "activity:read",
        "state": str(participant_id),
    }
    query = urlencode(params)
    return f"{STRAVA_AUTH_URL}?{query}"


def exchange_strava_code(code: str) -> _StravaTokenExchangeData:
    """Exchange an OAuth authorization code for access/refresh tokens.

    Args:
        code: The authorization code from Strava's OAuth redirect.

    Returns:
        Strava token response containing access_token, refresh_token,
        expires_at, and athlete info.
    """
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return cast("_StravaTokenExchangeData", resp.json())


def refresh_strava_token(strava_token: StravaToken) -> StravaToken:
    """Refresh an expired Strava access token.

    Updates the token record in-place and persists to the database.

    Args:
        strava_token: The StravaToken record with an expired access token.

    Returns:
        The updated StravaToken with fresh credentials.
    """
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": strava_token.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        data = cast("_StravaTokenRefreshData", resp.json())

    with get_session() as session:
        token = session.get(StravaToken, strava_token.id)
        if token is not None:
            token.access_token = data["access_token"]
            token.refresh_token = data["refresh_token"]
            token.expires_at = data["expires_at"]
            token.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
            logger.info(
                "strava_token_refreshed",
                participant_id=token.participant_id,
                expires_at=data["expires_at"],
            )
            # Return a detached copy of the updated values
            return StravaToken(
                id=token.id,
                participant_id=token.participant_id,
                strava_athlete_id=token.strava_athlete_id,
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                expires_at=token.expires_at,
                scope=token.scope,
                created_at=token.created_at,
                updated_at=token.updated_at,
            )

    # DB record was deleted between refresh and lookup — return fresh data
    logger.info(
        "strava_token_refreshed",
        participant_id=strava_token.participant_id,
        expires_at=data["expires_at"],
    )
    return StravaToken(
        id=strava_token.id,
        participant_id=strava_token.participant_id,
        strava_athlete_id=strava_token.strava_athlete_id,
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=data["expires_at"],
        scope=strava_token.scope,
        created_at=strava_token.created_at,
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )


def _get_valid_token(strava_token: StravaToken) -> StravaToken:
    """Ensure a StravaToken has a valid (non-expired) access token.

    Args:
        strava_token: The token to validate/refresh.

    Returns:
        A StravaToken with a valid access token.
    """
    if strava_token.is_expired:
        return refresh_strava_token(strava_token)
    return strava_token


def save_strava_token(
    participant_id: int,
    token_data: _StravaTokenExchangeData,
) -> StravaToken:
    """Save or update a Strava token for a participant.

    Args:
        participant_id: The participant's database ID.
        token_data: Response from Strava token exchange/refresh.

    Returns:
        The created or updated StravaToken record.
    """
    athlete_id = token_data["athlete"]["id"]

    with get_session() as session:
        existing = (
            session.query(StravaToken)
            .filter(StravaToken.participant_id == participant_id)
            .first()
        )
        if existing:
            existing.strava_athlete_id = athlete_id
            existing.access_token = token_data["access_token"]
            existing.refresh_token = token_data["refresh_token"]
            existing.expires_at = token_data["expires_at"]
            existing.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
            session.flush()
            logger.info(
                "strava_token_updated",
                participant_id=participant_id,
                athlete_id=athlete_id,
            )
            return StravaToken(
                id=existing.id,
                participant_id=existing.participant_id,
                strava_athlete_id=existing.strava_athlete_id,
                access_token=existing.access_token,
                refresh_token=existing.refresh_token,
                expires_at=existing.expires_at,
                scope=existing.scope,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )

        token = StravaToken(
            participant_id=participant_id,
            strava_athlete_id=athlete_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=token_data["expires_at"],
            scope=token_data.get("scope", "activity:read"),
        )
        session.add(token)
        session.flush()
        logger.info(
            "strava_token_created",
            participant_id=participant_id,
            athlete_id=athlete_id,
        )
        return StravaToken(
            id=token.id,
            participant_id=token.participant_id,
            strava_athlete_id=token.strava_athlete_id,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=token.expires_at,
            scope=token.scope,
            created_at=token.created_at,
            updated_at=token.updated_at,
        )


def fetch_strava_activities(
    strava_token: StravaToken,
    *,
    after: int | None = None,
    before: int | None = None,
) -> list[_StravaActivityData]:
    """Fetch activities from the Strava API.

    Args:
        strava_token: A valid StravaToken with access credentials.
        after: Unix timestamp — only return activities after this time.
        before: Unix timestamp — only return activities before this time.

    Returns:
        List of activity dicts from the Strava API.
    """
    token = _get_valid_token(strava_token)
    params: dict[str, int] = {"per_page": 100}
    if after is not None:
        params["after"] = after
    if before is not None:
        params["before"] = before

    all_activities: list[_StravaActivityData] = []
    page = 1

    with httpx.Client(timeout=15.0) as client:
        while True:
            params["page"] = page
            resp = client.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {token.access_token}"},
                params=params,
            )
            resp.raise_for_status()
            batch = cast("list[_StravaActivityData]", resp.json())
            if not batch:
                break
            all_activities.extend(batch)
            if len(batch) < 100:
                break
            page += 1

    return all_activities


def _date_to_weekday_field(dt: datetime.datetime) -> str:
    """Map a datetime to the corresponding WeeklySubmission day field name.

    Args:
        dt: A datetime in local time.

    Returns:
        Field name like "monday", "tuesday", etc.
    """
    return _WEEKDAY_TO_FIELD[dt.weekday()]


def _date_to_competition_week(dt: datetime.date) -> int | None:
    """Map a date to a competition week number (1-20).

    Args:
        dt: A date to check.

    Returns:
        Week number if within competition, None otherwise.
    """
    if dt < COMPETITION_START:
        return None
    days_elapsed = (dt - COMPETITION_START).days
    week = days_elapsed // 7 + 1
    if week > settings.week_max:
        return None
    return week


def sync_participant_activities(participant_id: int) -> int:
    """Sync a participant's Strava activities and auto-fill submissions.

    Fetches recent activities from Strava, stores them in the database,
    and updates (or creates) WeeklySubmission records by marking the
    corresponding day as exercised if the activity was 30+ minutes.

    Args:
        participant_id: The participant to sync.

    Returns:
        Number of new activities synced.

    Raises:
        ValueError: If the participant has no Strava connection.
    """
    with get_session() as session:
        strava_token = (
            session.query(StravaToken)
            .filter(StravaToken.participant_id == participant_id)
            .first()
        )
        if strava_token is None:
            msg = f"No Strava connection for participant {participant_id}"
            raise ValueError(msg)

        # Detach the token data we need before the session closes
        token_copy = StravaToken(
            id=strava_token.id,
            participant_id=strava_token.participant_id,
            strava_athlete_id=strava_token.strava_athlete_id,
            access_token=strava_token.access_token,
            refresh_token=strava_token.refresh_token,
            expires_at=strava_token.expires_at,
            scope=strava_token.scope,
            created_at=strava_token.created_at,
            updated_at=strava_token.updated_at,
        )

    # Fetch activities from competition start onward
    competition_start_ts = int(
        datetime.datetime.combine(
            COMPETITION_START,
            datetime.time.min,
            tzinfo=COMPETITION_TZ,
        ).timestamp()
    )

    activities = fetch_strava_activities(
        token_copy,
        after=competition_start_ts,
    )

    synced_count = 0
    weeks_modified: set[int] = set()

    with get_session() as session:
        for activity in activities:
            strava_id = activity["id"]
            moving_time = activity.get("moving_time", 0)
            duration_minutes = moving_time / _SECONDS_PER_MINUTE

            # Parse the local start time
            start_local_str = activity.get("start_date_local", "")
            try:
                start_local = datetime.datetime.fromisoformat(start_local_str)
            except (ValueError, AttributeError):
                logger.warning(
                    "strava_activity_bad_date",
                    strava_id=strava_id,
                    start_date=start_local_str,
                )
                continue

            activity_date = start_local.date()
            week_num = _date_to_competition_week(activity_date)
            if week_num is None:
                continue

            # Check if activity already exists
            existing_activity = (
                session.query(StravaActivity)
                .filter(StravaActivity.strava_activity_id == strava_id)
                .first()
            )
            if existing_activity is not None:
                continue

            # Store the activity
            new_activity = StravaActivity(
                participant_id=participant_id,
                strava_activity_id=strava_id,
                activity_type=activity.get("type", "Unknown"),
                name=activity.get("name", "Activity"),
                start_date_local=start_local,
                elapsed_time_seconds=activity.get("elapsed_time", 0),
                moving_time_seconds=moving_time,
                distance_meters=activity.get("distance"),
            )
            session.add(new_activity)
            synced_count += 1

            # Only auto-fill if activity meets minimum duration
            if duration_minutes >= settings.strava_min_activity_minutes:
                day_field = _date_to_weekday_field(start_local)
                _update_weekly_submission(session, participant_id, week_num, day_field)
                weeks_modified.add(week_num)

    if weeks_modified:
        standings_cache.invalidate()
        logger.info(
            "strava_sync_completed",
            participant_id=participant_id,
            activities_synced=synced_count,
            weeks_modified=sorted(weeks_modified),
        )

    return synced_count


def _update_weekly_submission(
    session: Session,
    participant_id: int,
    week_number: int,
    day_field: str,
) -> None:
    """Update or create a WeeklySubmission, marking a specific day as exercised.

    If a submission already exists for this participant/week, we update
    the day field to True (never set it back to False). If no submission
    exists, we create one with only the given day checked.

    Args:
        session: Active SQLAlchemy session.
        participant_id: The participant's database ID.
        week_number: Competition week number (1-20).
        day_field: Field name to mark as True (e.g. "monday").
    """
    submission = (
        session.query(WeeklySubmission)
        .filter(
            WeeklySubmission.participant_id == participant_id,
            WeeklySubmission.week_number == week_number,
        )
        .first()
    )

    if submission is not None:
        # Only set to True, never revert to False
        if not getattr(submission, day_field):
            setattr(submission, day_field, True)
            logger.info(
                "strava_day_marked",
                participant_id=participant_id,
                week=week_number,
                day=day_field,
                source="strava_update",
            )
    else:
        # Create a new submission with only this day checked
        kwargs = {
            "participant_id": participant_id,
            "week_number": week_number,
            day_field: True,
        }
        new_sub = WeeklySubmission(**kwargs)
        session.add(new_sub)
        logger.info(
            "strava_submission_created",
            participant_id=participant_id,
            week=week_number,
            day=day_field,
            source="strava_auto",
        )


def get_connected_participants() -> list[_ParticipantConnection]:
    """Get all participants and their Strava connection status.

    Returns:
        List of dicts with participant info and connection status.
    """
    with get_session() as session:
        participants = session.query(Participant).order_by(Participant.name).all()
        tokens = {t.participant_id: t for t in session.query(StravaToken).all()}

        result: list[_ParticipantConnection] = []
        for p in participants:
            token = tokens.get(p.id)
            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "strava_connected": token is not None,
                    "strava_athlete_id": token.strava_athlete_id if token else None,
                }
            )
        return result


def disconnect_strava(participant_id: int) -> bool:
    """Remove a participant's Strava connection.

    Deauthorizes the app on Strava's side and removes the local token.

    Args:
        participant_id: The participant to disconnect.

    Returns:
        True if a connection was removed, False if none existed.
    """
    with get_session() as session:
        token = (
            session.query(StravaToken)
            .filter(StravaToken.participant_id == participant_id)
            .first()
        )
        if token is None:
            return False

        # Try to deauthorize on Strava's side (best-effort)
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    STRAVA_DEAUTH_URL,
                    data={"access_token": token.access_token},
                )
        except httpx.HTTPError:
            logger.warning(
                "strava_deauth_failed",
                participant_id=participant_id,
            )

        session.delete(token)
        logger.info(
            "strava_disconnected",
            participant_id=participant_id,
        )
        return True


def sync_all_connected_participants() -> dict[str, int]:
    """Sync activities for all participants with a Strava connection.

    Returns:
        Dict mapping participant name to number of activities synced.
    """
    results: dict[str, int] = {}

    with get_session() as session:
        tokens = session.query(StravaToken).all()
        participant_ids = [(t.participant_id, t.id) for t in tokens]

    for participant_id, _token_id in participant_ids:
        try:
            count = sync_participant_activities(participant_id)
            with get_session() as session:
                p = session.get(Participant, participant_id)
                name = p.name if p else f"ID:{participant_id}"
            results[name] = count
        except Exception:
            logger.exception(
                "strava_sync_failed",
                participant_id=participant_id,
            )
            results[f"ID:{participant_id}"] = -1

    return results
