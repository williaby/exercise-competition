"""Application routes for the exercise competition.

All routes use sync ``def`` — FastAPI runs them in a threadpool.
Templates are imported via helper to avoid circular imports with main.py.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import TYPE_CHECKING, Annotated, Any, TypedDict

from fastapi import APIRouter, Form, Path, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError

from exercise_competition.core.config import settings
from exercise_competition.core.database import get_session
from exercise_competition.utils.logging import get_logger

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates
from exercise_competition.models import Participant, WeeklySubmission
from exercise_competition.services.cache import standings_cache
from exercise_competition.services.jokes import get_random_joke
from exercise_competition.services.scoring import (
    Standing,
    calculate_standings,
    get_current_week,
    get_week_label,
)

logger = get_logger(__name__)

_EXPECTED_TOKEN_PARTS = 2

router = APIRouter()

# CSRF secret: prefer env var for multi-worker consistency, fallback to per-process
_CSRF_SECRET = os.environ.get("CSRF_SECRET") or secrets.token_hex(32)


# ---------------------------------------------------------------------------
# TypedDicts for template contexts
# ---------------------------------------------------------------------------


class SubmitContext(TypedDict):
    """Template context for the submit form."""

    participants: list[str]
    weeks: list[tuple[int, str]]
    current_week: int
    csrf_token: str
    error: str | None
    success: str | None


class LeaderboardContext(TypedDict):
    """Template context for the leaderboard page."""

    standings: list[Standing]
    current_week: int | None
    success: str | None
    joke: str


class WeekDayEntry(TypedDict):
    """A single participant's data for a week view."""

    name: str
    submitted: bool
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    days_exercised: int
    is_compliant: bool


class WeekViewContext(TypedDict):
    """Template context for the week detail view."""

    week_number: int
    week_data: list[WeekDayEntry]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(typed_dict: Any) -> dict[str, Any]:
    """Cast a TypedDict to a plain dict for Jinja2 TemplateResponse compatibility."""
    return dict(typed_dict)


def _get_templates() -> Jinja2Templates:
    """Get the templates instance, avoiding circular import."""
    from exercise_competition.main import templates  # noqa: PLC0415

    return templates


def _generate_csrf_token() -> str:
    """Generate a time-limited CSRF token."""
    timestamp = str(int(time.time()))
    raw = f"{_CSRF_SECRET}:{timestamp}"
    sig = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"{timestamp}:{sig}"


def _validate_csrf_token(token: str) -> bool:
    """Validate a CSRF token is authentic and not expired."""
    parts = token.split(":")
    if len(parts) != _EXPECTED_TOKEN_PARTS:
        return False
    timestamp_str, sig = parts
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False
    if time.time() - timestamp > settings.csrf_ttl_seconds:
        return False
    expected_raw = f"{_CSRF_SECRET}:{timestamp_str}"
    expected_sig = hashlib.sha256(expected_raw.encode()).hexdigest()[:32]
    return secrets.compare_digest(sig, expected_sig)


def _get_participant_names() -> list[str]:
    """Fetch all participant names from the database, sorted alphabetically."""
    with get_session() as session:
        participants = session.query(Participant).order_by(Participant.name).all()
        return [p.name for p in participants]


def _build_submit_context(
    *,
    error: str | None = None,
    success: str | None = None,
) -> SubmitContext:
    """Build the template context for the submit form.

    Args:
        error: Optional error message to display.
        success: Optional success message to display.

    Returns:
        A typed context dict for the submit template.
    """
    current_week = get_current_week()
    return SubmitContext(
        participants=_get_participant_names(),
        weeks=[
            (w, get_week_label(w))
            for w in range(settings.week_min, settings.week_max + 1)
        ],
        current_week=current_week or 1,
        csrf_token=_generate_csrf_token(),
        error=error,
        success=success,
    )


def _validate_participant_name(name: str) -> Participant | None:
    """Look up and return a Participant by name, or None if not found.

    This validates the submitted name against real database records,
    preventing arbitrary name injection.

    Args:
        name: The participant name to look up.

    Returns:
        The Participant ORM object, or None.
    """
    with get_session() as session:
        return (
            session.query(Participant)
            .filter(Participant.name == name)
            .first()
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_class=RedirectResponse)
def index() -> RedirectResponse:
    """Redirect root to leaderboard."""
    return RedirectResponse(url="/leaderboard", status_code=302)


@router.get("/submit", response_class=HTMLResponse)
def submit_form(request: Request) -> HTMLResponse:
    """Render the weekly exercise submission form."""
    templates = _get_templates()
    context = _build_submit_context()
    return templates.TemplateResponse(request, "submit.html", _ctx(context))


@router.post("/submit", response_class=HTMLResponse, response_model=None)
def submit_exercise(
    request: Request,
    csrf_token: Annotated[str, Form()],
    participant_name: Annotated[str, Form(max_length=100)],
    week_number: Annotated[int, Form()],
    monday: Annotated[bool, Form()] = False,
    tuesday: Annotated[bool, Form()] = False,
    wednesday: Annotated[bool, Form()] = False,
    thursday: Annotated[bool, Form()] = False,
    friday: Annotated[bool, Form()] = False,
    saturday: Annotated[bool, Form()] = False,
    sunday: Annotated[bool, Form()] = False,
) -> HTMLResponse | RedirectResponse:
    """Process a weekly exercise submission."""
    templates = _get_templates()

    # CSRF validation
    if not _validate_csrf_token(csrf_token):
        logger.warning("csrf_validation_failed", participant=participant_name)
        context = _build_submit_context(
            error="Invalid form submission. Please try again.",
        )
        return templates.TemplateResponse(request, "submit.html", _ctx(context))

    # Week range validation
    if week_number < settings.week_min or week_number > settings.week_max:
        logger.warning(
            "invalid_week_number",
            participant=participant_name,
            week_number=week_number,
        )
        context = _build_submit_context(
            error=f"Week number must be between {settings.week_min} and {settings.week_max}.",
        )
        return templates.TemplateResponse(request, "submit.html", _ctx(context))

    # Participant validation — must match a known database record
    participant = _validate_participant_name(participant_name)
    if participant is None:
        logger.warning(
            "unknown_participant_rejected",
            participant=participant_name,
        )
        context = _build_submit_context(
            error=f"Unknown participant: {participant_name}",
        )
        return templates.TemplateResponse(request, "submit.html", _ctx(context))

    with get_session() as session:
        submission = WeeklySubmission(
            participant_id=participant.id,
            week_number=week_number,
            monday=monday,
            tuesday=tuesday,
            wednesday=wednesday,
            thursday=thursday,
            friday=friday,
            saturday=saturday,
            sunday=sunday,
        )
        session.add(submission)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            error_detail = str(exc.orig) if exc.orig else str(exc)
            if "uq_participant_week" in error_detail.lower() or "unique" in error_detail.lower():
                logger.warning(
                    "duplicate_submission_rejected",
                    participant=participant_name,
                    week_number=week_number,
                )
                context = _build_submit_context(
                    error=f"{participant_name} has already submitted for week {week_number}.",
                )
            else:
                logger.exception(
                    "integrity_error_on_submission",
                    participant=participant_name,
                    week_number=week_number,
                    error=error_detail,
                )
                context = _build_submit_context(
                    error="An unexpected error occurred. Please try again.",
                )
            return templates.TemplateResponse(request, "submit.html", _ctx(context))

        # Invalidate leaderboard cache after successful submission
        standings_cache.invalidate()

        logger.info(
            "exercise_submitted",
            participant=participant_name,
            participant_id=participant.id,
            week_number=week_number,
            days_exercised=submission.days_exercised,
            is_compliant=submission.is_compliant,
        )

    return RedirectResponse(url="/leaderboard?msg=success", status_code=303)


@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard(
    request: Request,
    msg: Annotated[str | None, Query(max_length=20, pattern=r"^[a-z]+$")] = None,
) -> HTMLResponse:
    """Render the competition leaderboard."""
    templates = _get_templates()

    # Use cached standings when available
    standings = standings_cache.get()
    if standings is None:
        with get_session() as session:
            participants = session.query(Participant).order_by(Participant.name).all()
            participant_tuples = [(p.id, p.name) for p in participants]
            submissions = session.query(WeeklySubmission).all()
            standings = calculate_standings(submissions, participant_tuples)
        standings_cache.set(standings)

    current_week = get_current_week()
    success_msg = "Submission recorded!" if msg == "success" else None

    context = LeaderboardContext(
        standings=standings,
        current_week=current_week,
        success=success_msg,
        joke=get_random_joke(),
    )
    return templates.TemplateResponse(request, "leaderboard.html", _ctx(context))


@router.get("/week/{week_number}", response_class=HTMLResponse)
def week_view(
    request: Request,
    week_number: Annotated[int, Path(ge=settings.week_min, le=settings.week_max)],
) -> HTMLResponse:
    """Show all submissions for a specific week."""
    templates = _get_templates()

    with get_session() as session:
        submissions = (
            session.query(WeeklySubmission)
            .filter(WeeklySubmission.week_number == week_number)
            .all()
        )
        sub_map = {s.participant_id: s for s in submissions}

        participants = session.query(Participant).order_by(Participant.name).all()

        week_data: list[WeekDayEntry] = []
        for p in participants:
            sub = sub_map.get(p.id)
            week_data.append(
                WeekDayEntry(
                    name=p.name,
                    submitted=sub is not None,
                    monday=getattr(sub, "monday", False),
                    tuesday=getattr(sub, "tuesday", False),
                    wednesday=getattr(sub, "wednesday", False),
                    thursday=getattr(sub, "thursday", False),
                    friday=getattr(sub, "friday", False),
                    saturday=getattr(sub, "saturday", False),
                    sunday=getattr(sub, "sunday", False),
                    days_exercised=sub.days_exercised if sub else 0,
                    is_compliant=sub.is_compliant if sub else False,
                )
            )

    context = WeekViewContext(
        week_number=week_number,
        week_data=week_data,
    )
    return templates.TemplateResponse(request, "week.html", _ctx(context))
