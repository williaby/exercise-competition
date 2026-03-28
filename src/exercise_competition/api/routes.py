"""Application routes for the exercise competition.

All routes use sync ``def`` — FastAPI runs them in a threadpool.
Templates are imported via helper to avoid circular imports with main.py.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError

from exercise_competition.core.database import get_session

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates
from exercise_competition.models import Participant, WeeklySubmission
from exercise_competition.services.scoring import (
    calculate_standings,
    get_current_week,
    get_week_label,
)

_WEEK_MIN = 1
_WEEK_MAX = 20
_EXPECTED_TOKEN_PARTS = 2

router = APIRouter()

# Simple CSRF: per-process secret, tokens valid for 1 hour
_CSRF_SECRET = secrets.token_hex(32)
_CSRF_TTL = 3600


def _get_templates() -> Jinja2Templates:
    """Get the templates instance, avoiding circular import."""
    from exercise_competition.main import templates  # noqa: PLC0415

    return templates


def _generate_csrf_token() -> str:
    """Generate a time-limited CSRF token."""
    timestamp = str(int(time.time()))
    raw = f"{_CSRF_SECRET}:{timestamp}"
    sig = hashlib.sha256(raw.encode()).hexdigest()[:16]
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
    if time.time() - timestamp > _CSRF_TTL:
        return False
    expected_raw = f"{_CSRF_SECRET}:{timestamp_str}"
    expected_sig = hashlib.sha256(expected_raw.encode()).hexdigest()[:16]
    return secrets.compare_digest(sig, expected_sig)


@router.get("/", response_class=RedirectResponse)
def index() -> RedirectResponse:
    """Redirect root to leaderboard."""
    return RedirectResponse(url="/leaderboard", status_code=302)


@router.get("/submit", response_class=HTMLResponse)
def submit_form(request: Request) -> HTMLResponse:
    """Render the weekly exercise submission form."""
    templates = _get_templates()

    with get_session() as session:
        participants = session.query(Participant).order_by(Participant.name).all()
        participant_names = [p.name for p in participants]

    current_week = get_current_week()
    csrf_token = _generate_csrf_token()

    return templates.TemplateResponse(
        request,
        "submit.html",
        {
            "participants": participant_names,
            "weeks": [(w, get_week_label(w)) for w in range(1, 21)],
            "current_week": current_week or 1,
            "csrf_token": csrf_token,
            "error": None,
            "success": None,
        },
    )


@router.post("/submit", response_class=HTMLResponse, response_model=None)
def submit_exercise(
    request: Request,
    csrf_token: str = Form(...),
    participant_name: str = Form(...),
    week_number: int = Form(...),
    monday: bool = Form(default=False),
    tuesday: bool = Form(default=False),
    wednesday: bool = Form(default=False),
    thursday: bool = Form(default=False),
    friday: bool = Form(default=False),
    saturday: bool = Form(default=False),
    sunday: bool = Form(default=False),
) -> HTMLResponse | RedirectResponse:
    """Process a weekly exercise submission."""
    templates = _get_templates()

    # CSRF validation
    if not _validate_csrf_token(csrf_token):
        return _render_submit_with_error(
            request, templates, "Invalid form submission. Please try again."
        )

    # Week range validation
    if week_number < _WEEK_MIN or week_number > _WEEK_MAX:
        return _render_submit_with_error(
            request, templates, "Week number must be between 1 and 20."
        )

    with get_session() as session:
        participant = (
            session.query(Participant)
            .filter(Participant.name == participant_name)
            .first()
        )
        if participant is None:
            return _render_submit_with_error(
                request, templates, f"Unknown participant: {participant_name}"
            )

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
        except IntegrityError:
            session.rollback()
            return _render_submit_with_error(
                request,
                templates,
                f"{participant_name} has already submitted for week {week_number}.",
            )

    return RedirectResponse(url="/leaderboard?msg=success", status_code=303)


def _render_submit_with_error(
    request: Request,
    templates: Jinja2Templates,
    error: str,
) -> HTMLResponse:
    """Re-render the submit form with an error message."""
    with get_session() as session:
        participants = session.query(Participant).order_by(Participant.name).all()
        participant_names = [p.name for p in participants]

    current_week = get_current_week()
    csrf_token = _generate_csrf_token()

    return templates.TemplateResponse(
        request,
        "submit.html",
        {
            "participants": participant_names,
            "weeks": [(w, get_week_label(w)) for w in range(1, 21)],
            "current_week": current_week or 1,
            "csrf_token": csrf_token,
            "error": error,
            "success": None,
        },
    )


@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard(
    request: Request,
    msg: str | None = Query(None),
) -> HTMLResponse:
    """Render the competition leaderboard."""
    templates = _get_templates()

    with get_session() as session:
        participants = session.query(Participant).order_by(Participant.name).all()
        participant_tuples = [(p.id, p.name) for p in participants]
        submissions = session.query(WeeklySubmission).all()
        standings = calculate_standings(submissions, participant_tuples)

    current_week = get_current_week()
    success_msg = "Submission recorded!" if msg == "success" else None

    return templates.TemplateResponse(
        request,
        "leaderboard.html",
        {
            "standings": standings,
            "current_week": current_week,
            "success": success_msg,
        },
    )


@router.get("/week/{week_number}", response_class=HTMLResponse)
def week_view(
    request: Request,
    week_number: int,
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

        week_data = []
        for p in participants:
            sub = sub_map.get(p.id)
            week_data.append(
                {
                    "name": p.name,
                    "submitted": sub is not None,
                    "monday": getattr(sub, "monday", False),
                    "tuesday": getattr(sub, "tuesday", False),
                    "wednesday": getattr(sub, "wednesday", False),
                    "thursday": getattr(sub, "thursday", False),
                    "friday": getattr(sub, "friday", False),
                    "saturday": getattr(sub, "saturday", False),
                    "sunday": getattr(sub, "sunday", False),
                    "days_exercised": sub.days_exercised if sub else 0,
                    "is_compliant": sub.is_compliant if sub else False,
                }
            )

    return templates.TemplateResponse(
        request,
        "week.html",
        {
            "week_number": week_number,
            "week_data": week_data,
        },
    )
