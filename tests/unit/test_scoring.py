"""Unit tests for the scoring service."""

from __future__ import annotations

import datetime
from unittest.mock import patch

from exercise_competition.services.scoring import (
    COMPETITION_TZ,
    Standing,
    _calculate_streak,
    calculate_standings,
    days_exercised,
    get_current_week,
    is_compliant,
)


class FakeSubmission:
    """Minimal stand-in for WeeklySubmission for unit tests."""

    def __init__(
        self,
        participant_id=1,
        week_number=1,
        monday=False,
        tuesday=False,
        wednesday=False,
        thursday=False,
        friday=False,
        saturday=False,
        sunday=False,
    ):
        self.participant_id = participant_id
        self.week_number = week_number
        self.monday = monday
        self.tuesday = tuesday
        self.wednesday = wednesday
        self.thursday = thursday
        self.friday = friday
        self.saturday = saturday
        self.sunday = sunday


class TestGetCurrentWeek:
    """Tests for get_current_week()."""

    def test_before_competition(self):
        fake_now = datetime.datetime(2026, 3, 29, 12, 0, tzinfo=COMPETITION_TZ)
        with patch("exercise_competition.services.scoring.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = fake_now
            mock_dt.date = datetime.date
            result = get_current_week()
        assert result is None

    def test_week_1_first_day(self):
        fake_now = datetime.datetime(2026, 3, 30, 8, 0, tzinfo=COMPETITION_TZ)
        with patch("exercise_competition.services.scoring.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = fake_now
            mock_dt.date = datetime.date
            result = get_current_week()
        assert result == 1

    def test_week_1_last_day(self):
        fake_now = datetime.datetime(2026, 4, 5, 23, 59, tzinfo=COMPETITION_TZ)
        with patch("exercise_competition.services.scoring.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = fake_now
            mock_dt.date = datetime.date
            result = get_current_week()
        assert result == 1

    def test_week_2_first_day(self):
        fake_now = datetime.datetime(2026, 4, 6, 0, 0, tzinfo=COMPETITION_TZ)
        with patch("exercise_competition.services.scoring.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = fake_now
            mock_dt.date = datetime.date
            result = get_current_week()
        assert result == 2

    def test_week_20(self):
        fake_now = datetime.datetime(2026, 8, 10, 12, 0, tzinfo=COMPETITION_TZ)
        with patch("exercise_competition.services.scoring.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = fake_now
            mock_dt.date = datetime.date
            result = get_current_week()
        assert result == 20

    def test_after_competition(self):
        fake_now = datetime.datetime(2026, 8, 17, 0, 0, tzinfo=COMPETITION_TZ)
        with patch("exercise_competition.services.scoring.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = fake_now
            mock_dt.date = datetime.date
            result = get_current_week()
        assert result is None


class TestDaysExercised:
    """Tests for days_exercised()."""

    def test_zero_days(self):
        sub = FakeSubmission()
        assert days_exercised(sub) == 0

    def test_all_seven_days(self):
        sub = FakeSubmission(
            monday=True,
            tuesday=True,
            wednesday=True,
            thursday=True,
            friday=True,
            saturday=True,
            sunday=True,
        )
        assert days_exercised(sub) == 7

    def test_three_days(self):
        sub = FakeSubmission(monday=True, wednesday=True, friday=True)
        assert days_exercised(sub) == 3

    def test_one_day(self):
        sub = FakeSubmission(saturday=True)
        assert days_exercised(sub) == 1


class TestIsCompliant:
    """Tests for is_compliant()."""

    def test_zero_days_not_compliant(self):
        sub = FakeSubmission()
        assert is_compliant(sub) is False

    def test_one_day_not_compliant(self):
        sub = FakeSubmission(monday=True)
        assert is_compliant(sub) is False

    def test_two_days_compliant(self):
        sub = FakeSubmission(monday=True, tuesday=True)
        assert is_compliant(sub) is True

    def test_three_days_compliant(self):
        sub = FakeSubmission(monday=True, tuesday=True, wednesday=True)
        assert is_compliant(sub) is True


class TestCalculateStreak:
    """Tests for _calculate_streak()."""

    def test_empty_submissions(self):
        assert _calculate_streak([]) == 0

    def test_single_compliant_week(self):
        subs = [FakeSubmission(week_number=1, monday=True, tuesday=True)]
        assert _calculate_streak(subs) == 1

    def test_single_noncompliant_week(self):
        subs = [FakeSubmission(week_number=1, monday=True)]
        assert _calculate_streak(subs) == 0

    def test_consecutive_compliant(self):
        subs = [
            FakeSubmission(week_number=1, monday=True, tuesday=True),
            FakeSubmission(week_number=2, wednesday=True, thursday=True),
            FakeSubmission(week_number=3, friday=True, saturday=True),
        ]
        assert _calculate_streak(subs) == 3

    def test_gap_breaks_streak(self):
        subs = [
            FakeSubmission(week_number=1, monday=True, tuesday=True),
            # week 2 missing
            FakeSubmission(week_number=3, wednesday=True, thursday=True),
        ]
        assert _calculate_streak(subs) == 1  # Only week 3 counts

    def test_noncompliant_breaks_streak(self):
        subs = [
            FakeSubmission(week_number=1, monday=True, tuesday=True),
            FakeSubmission(week_number=2, monday=True),  # Only 1 day
            FakeSubmission(week_number=3, wednesday=True, thursday=True),
        ]
        assert _calculate_streak(subs) == 1  # Only week 3 counts


class TestCalculateStandings:
    """Tests for calculate_standings()."""

    def test_no_submissions(self):
        participants = [(1, "Alice"), (2, "Bob")]
        standings = calculate_standings([], participants)
        assert len(standings) == 2
        assert all(s.points == 0 for s in standings)
        assert all(s.avg_days == 0.0 for s in standings)

    def test_sort_by_points(self):
        participants = [(1, "Alice"), (2, "Bob")]
        subs = [
            # Alice: 2 compliant weeks
            FakeSubmission(participant_id=1, week_number=1, monday=True, tuesday=True),
            FakeSubmission(participant_id=1, week_number=2, monday=True, tuesday=True),
            # Bob: 1 compliant week
            FakeSubmission(participant_id=2, week_number=1, monday=True, tuesday=True),
        ]
        standings = calculate_standings(subs, participants)
        assert standings[0].name == "Alice"
        assert standings[0].points == 2
        assert standings[1].name == "Bob"
        assert standings[1].points == 1

    def test_tiebreaker_avg_days(self):
        participants = [(1, "Alice"), (2, "Bob")]
        subs = [
            # Both compliant week 1, but Alice has more days
            FakeSubmission(
                participant_id=1,
                week_number=1,
                monday=True,
                tuesday=True,
                wednesday=True,
            ),
            FakeSubmission(
                participant_id=2,
                week_number=1,
                monday=True,
                tuesday=True,
            ),
        ]
        standings = calculate_standings(subs, participants)
        assert standings[0].name == "Alice"
        assert standings[0].avg_days == 3.0
        assert standings[1].name == "Bob"
        assert standings[1].avg_days == 2.0

    def test_avg_days_only_submitted_weeks(self):
        participants = [(1, "Alice")]
        subs = [
            FakeSubmission(
                participant_id=1,
                week_number=1,
                monday=True,
                tuesday=True,
                wednesday=True,
            ),
            FakeSubmission(
                participant_id=1,
                week_number=3,
                monday=True,
                tuesday=True,
                wednesday=True,
                thursday=True,
                friday=True,
            ),
        ]
        standings = calculate_standings(subs, participants)
        # (3 + 5) / 2 = 4.0 (only 2 submitted weeks, not 3)
        assert standings[0].avg_days == 4.0
        assert standings[0].weeks_submitted == 2

    def test_standing_dataclass(self):
        s = Standing(
            participant_id=1,
            name="Test",
            points=5,
            avg_days=3.5,
            streak=3,
            weeks_submitted=5,
        )
        assert s.participant_id == 1
        assert s.name == "Test"
        assert s.points == 5
        assert s.avg_days == 3.5
        assert s.streak == 3
        assert s.weeks_submitted == 5
