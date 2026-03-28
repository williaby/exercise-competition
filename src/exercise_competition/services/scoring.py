"""Competition scoring, compliance, and standings logic.

Encodes the competition rules:
- Configurable week count (default 20) starting Monday 2026-03-30
- Compliance: configurable threshold (default 2+) exercise days per week = 1 point
- Tiebreaker: average exercise days per submitted week
- Streak: consecutive compliant weeks counting backward from most recent

Competition parameters are driven by ``Settings`` (see ``core.config``).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from exercise_competition.models import WeeklySubmission

COMPETITION_START = datetime.date(2026, 3, 30)
COMPETITION_TZ = ZoneInfo("America/Chicago")

DAY_FIELDS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _get_total_weeks() -> int:
    """Return the configured total weeks from settings."""
    from exercise_competition.core.config import settings  # noqa: PLC0415

    return settings.week_max


def _get_compliance_threshold() -> int:
    """Return the configured compliance threshold from settings."""
    from exercise_competition.core.config import settings  # noqa: PLC0415

    return settings.compliance_threshold


@dataclass(frozen=True)
class Standing:
    """A participant's current competition standing.

    Attributes:
        participant_id: Database ID of the participant.
        name: Participant display name.
        points: Number of compliant weeks.
        avg_days: Average exercise days per submitted week.
        streak: Consecutive compliant weeks from most recent backward.
        weeks_submitted: Number of weeks with submissions.
    """

    participant_id: int
    name: str
    points: int
    avg_days: float
    streak: int
    weeks_submitted: int


def get_week_date_range(week: int) -> tuple[datetime.date, datetime.date]:
    """Get the start (Mon) and end (Sun) dates for a competition week.

    Args:
        week: Week number (1-based).

    Returns:
        Tuple of (start_date, end_date) for that week.
    """
    start = COMPETITION_START + datetime.timedelta(weeks=week - 1)
    end = start + datetime.timedelta(days=6)
    return start, end


def get_week_label(week: int) -> str:
    """Get a display label for a competition week with date range.

    Args:
        week: Week number (1-based).

    Returns:
        Label like "Week 1 (3/30 - 4/5)".
    """
    start, end = get_week_date_range(week)
    return f"Week {week} ({start.month}/{start.day} - {end.month}/{end.day})"


def get_current_week() -> int | None:
    """Get the current competition week number.

    Returns:
        The week number if within the competition period, or None if
        before or after the competition.
    """
    today = datetime.datetime.now(tz=COMPETITION_TZ).date()
    if today < COMPETITION_START:
        return None
    days_elapsed = (today - COMPETITION_START).days
    week = days_elapsed // 7 + 1
    if week > _get_total_weeks():
        return None
    return week


def days_exercised(submission: WeeklySubmission) -> int:
    """Count exercise days in a submission.

    Args:
        submission: A weekly submission record.

    Returns:
        Number of days marked as exercised (0-7).
    """
    return sum(getattr(submission, field) for field in DAY_FIELDS)


def is_compliant(submission: WeeklySubmission) -> bool:
    """Check if a submission meets the weekly compliance threshold.

    The threshold is configurable via ``settings.compliance_threshold``
    (default: 2 days).

    Args:
        submission: A weekly submission record.

    Returns:
        True if the participant met or exceeded the compliance threshold.
    """
    return days_exercised(submission) >= _get_compliance_threshold()


def _calculate_streak(
    submissions: Sequence[WeeklySubmission],
) -> int:
    """Calculate consecutive compliant weeks from most recent backward.

    Missing weeks (no submission) break the streak.

    Args:
        submissions: Submissions for a single participant, any order.

    Returns:
        Length of the current compliant streak.
    """
    if not submissions:
        return 0

    by_week: dict[int, WeeklySubmission] = {s.week_number: s for s in submissions}
    max_week = max(by_week)

    streak = 0
    for week_num in range(max_week, 0, -1):
        sub = by_week.get(week_num)
        if sub is None or not is_compliant(sub):
            break
        streak += 1
    return streak


def calculate_standings(
    all_submissions: Sequence[WeeklySubmission],
    participants: Sequence[tuple[int, str]],
) -> list[Standing]:
    """Compute leaderboard standings for all participants.

    Args:
        all_submissions: All weekly submissions across all participants.
        participants: Sequence of (participant_id, name) tuples.

    Returns:
        List of Standing objects sorted by points desc, then avg_days desc.
    """
    by_participant: dict[int, list[WeeklySubmission]] = {
        pid: [] for pid, _ in participants
    }
    for sub in all_submissions:
        if sub.participant_id in by_participant:
            by_participant[sub.participant_id].append(sub)

    standings: list[Standing] = []
    for pid, name in participants:
        subs = by_participant[pid]
        points = sum(1 for s in subs if is_compliant(s))
        total_days = sum(days_exercised(s) for s in subs)
        weeks_submitted = len(subs)
        avg_days = total_days / weeks_submitted if weeks_submitted > 0 else 0.0
        streak = _calculate_streak(subs)

        standings.append(
            Standing(
                participant_id=pid,
                name=name,
                points=points,
                avg_days=round(avg_days, 2),
                streak=streak,
                weeks_submitted=weeks_submitted,
            )
        )

    standings.sort(key=lambda s: (s.points, s.avg_days), reverse=True)
    return standings
