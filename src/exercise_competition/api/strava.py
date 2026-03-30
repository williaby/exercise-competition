"""Strava OAuth and webhook routes.

Handles the OAuth 2.0 flow for connecting Strava accounts,
webhook subscription for real-time activity updates, and
manual sync triggers.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from exercise_competition.core.config import settings
from exercise_competition.core.database import get_session
from exercise_competition.models import Participant
from exercise_competition.services.strava import (
    disconnect_strava,
    exchange_strava_code,
    get_connected_participants,
    get_strava_auth_url,
    save_strava_token,
    sync_all_connected_participants,
    sync_participant_activities,
)
from exercise_competition.utils.logging import get_logger

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

_STRAVA_AUTH_ERROR_URL = "/strava?msg=auth_error"

logger = get_logger(__name__)

router = APIRouter(prefix="/strava", tags=["strava"])


def _get_templates() -> Jinja2Templates:
    """Get the templates instance, avoiding circular import."""
    from exercise_competition.main import templates

    return templates


# ---------------------------------------------------------------------------
# Strava settings page
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
def strava_settings(
    request: Request,
    msg: Annotated[str | None, Query(max_length=50)] = None,
) -> HTMLResponse:
    """Render the Strava connection management page."""
    templates = _get_templates()
    participants = get_connected_participants()
    strava_configured = bool(settings.strava_client_id)

    return templates.TemplateResponse(
        request,
        "strava.html",
        {
            "participants": participants,
            "strava_configured": strava_configured,
            "msg": msg,
        },
    )


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------


@router.get("/connect/{participant_id}", response_class=RedirectResponse)
def strava_connect(participant_id: int) -> RedirectResponse:
    """Redirect participant to Strava OAuth authorization page.

    Args:
        participant_id: ID of the participant initiating the connection.

    Returns:
        Redirect to Strava's authorization page.
    """
    if not settings.strava_client_id:
        return RedirectResponse(
            url="/strava?msg=strava_not_configured", status_code=302
        )

    # Validate participant exists
    with get_session() as session:
        participant = session.get(Participant, participant_id)
        if participant is None:
            return RedirectResponse(
                url="/strava?msg=invalid_participant", status_code=302
            )

    auth_url = get_strava_auth_url(participant_id)
    return RedirectResponse(
        url=auth_url, status_code=302
    )  # NOSONAR(S5146) redirect to Strava OAuth, URL built from config not user input


@router.get("/callback", response_class=RedirectResponse)
def strava_callback(
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """Handle Strava OAuth callback after user authorization.

    Args:
        code: Authorization code from Strava.
        state: Participant ID passed as state parameter.
        error: Error message if authorization was denied.

    Returns:
        Redirect to Strava settings page with status message.
    """
    if error:
        logger.warning("strava_auth_denied", error=error)
        return RedirectResponse(url="/strava?msg=auth_denied", status_code=302)

    if not code or not state:
        logger.warning(
            "strava_callback_missing_params", code=bool(code), state=bool(state)
        )
        return RedirectResponse(url=_STRAVA_AUTH_ERROR_URL, status_code=302)

    try:
        participant_id = int(state)
    except ValueError:
        logger.warning("strava_callback_invalid_state", state=state)
        return RedirectResponse(url=_STRAVA_AUTH_ERROR_URL, status_code=302)

    # Validate participant exists
    with get_session() as session:
        participant = session.get(Participant, participant_id)
        if participant is None:
            return RedirectResponse(
                url="/strava?msg=invalid_participant", status_code=302
            )

    try:
        token_data = exchange_strava_code(code)
        save_strava_token(participant_id, token_data)

        # Immediately sync activities
        try:
            synced = sync_participant_activities(participant_id)
            logger.info(
                "strava_initial_sync",
                participant_id=participant_id,
                activities_synced=synced,
            )
        except Exception:
            logger.exception(
                "strava_initial_sync_failed",
                participant_id=participant_id,
            )

        return RedirectResponse(url="/strava?msg=connected", status_code=302)
    except Exception:
        logger.exception(
            "strava_token_exchange_failed",
            participant_id=participant_id,
        )
        return RedirectResponse(url=_STRAVA_AUTH_ERROR_URL, status_code=302)


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------


@router.post("/disconnect/{participant_id}", response_class=RedirectResponse)
def strava_disconnect(participant_id: int) -> RedirectResponse:
    """Disconnect a participant's Strava account.

    Args:
        participant_id: ID of the participant to disconnect.

    Returns:
        Redirect to Strava settings page.
    """
    removed = disconnect_strava(participant_id)
    msg = "disconnected" if removed else "not_connected"
    return RedirectResponse(url=f"/strava?msg={msg}", status_code=303)


# ---------------------------------------------------------------------------
# Manual sync
# ---------------------------------------------------------------------------


@router.post("/sync", response_class=RedirectResponse)
def strava_sync_all() -> RedirectResponse:
    """Manually trigger a sync for all connected participants.

    Returns:
        Redirect to Strava settings page with sync result.
    """
    try:
        results = sync_all_connected_participants()
        total = sum(v for v in results.values() if v >= 0)
        logger.info("strava_manual_sync", results=results, total=total)
        return RedirectResponse(url=f"/strava?msg=synced_{total}", status_code=303)
    except Exception:
        logger.exception("strava_sync_all_failed")
        return RedirectResponse(url="/strava?msg=sync_error", status_code=303)


@router.post("/sync/{participant_id}", response_class=RedirectResponse)
def strava_sync_one(participant_id: int) -> RedirectResponse:
    """Manually trigger a sync for a single participant.

    Args:
        participant_id: ID of the participant to sync.

    Returns:
        Redirect to Strava settings page.
    """
    try:
        synced = sync_participant_activities(participant_id)
        return RedirectResponse(
            url=f"/strava?msg=synced_{synced}",
            status_code=303,
        )
    except ValueError:
        return RedirectResponse(url="/strava?msg=not_connected", status_code=303)
    except Exception:
        logger.exception(
            "strava_sync_one_failed",
            participant_id=participant_id,
        )
        return RedirectResponse(url="/strava?msg=sync_error", status_code=303)


# ---------------------------------------------------------------------------
# Webhook (for real-time activity updates from Strava)
# ---------------------------------------------------------------------------


@router.get("/webhook", response_class=JSONResponse)
def strava_webhook_verify(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
) -> JSONResponse:
    """Handle Strava webhook subscription verification.

    Strava sends a GET request with a challenge to verify the webhook.

    Args:
        hub_mode: Should be "subscribe".
        hub_challenge: Challenge string to echo back.
        hub_verify_token: Token to validate the request.

    Returns:
        JSON response echoing the challenge.
    """
    if hub_mode != "subscribe":
        return JSONResponse({"error": "invalid mode"}, status_code=400)

    expected = settings.strava_webhook_verify_token or ""
    if not secrets.compare_digest(hub_verify_token or "", expected):
        logger.warning("strava_webhook_invalid_verify_token")
        return JSONResponse({"error": "invalid verify token"}, status_code=403)

    return JSONResponse({"hub.challenge": hub_challenge})


@router.post("/webhook", response_class=JSONResponse)
def strava_webhook_event() -> JSONResponse:
    """Handle incoming Strava webhook events.

    Strava sends POST requests when activities are created, updated, or deleted.
    We acknowledge immediately and rely on periodic syncs to fetch new data.

    Returns:
        200 OK (Strava requires a 200 response within 2 seconds).
    """
    logger.info("strava_webhook_received")

    # Acknowledge the webhook immediately. Actual activity processing
    # is handled by manual or periodic sync_all_connected_participants().
    # For a more robust implementation, use FastAPI BackgroundTasks
    # to process the event asynchronously.
    return JSONResponse({"status": "ok"}, status_code=200)
