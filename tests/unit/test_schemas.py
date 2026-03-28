"""Unit tests for Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from exercise_competition.schemas import SubmissionForm


class TestSubmissionForm:
    """Tests for the SubmissionForm schema."""

    def test_valid_submission(self):
        form = SubmissionForm(
            participant_name="Byron Williams",
            week_number=1,
            monday=True,
            wednesday=True,
        )
        assert form.participant_name == "Byron Williams"
        assert form.week_number == 1
        assert form.monday is True
        assert form.tuesday is False
        assert form.wednesday is True

    def test_days_default_false(self):
        form = SubmissionForm(participant_name="Test", week_number=5)
        assert form.monday is False
        assert form.tuesday is False
        assert form.wednesday is False
        assert form.thursday is False
        assert form.friday is False
        assert form.saturday is False
        assert form.sunday is False

    def test_week_too_low(self):
        with pytest.raises(ValidationError):
            SubmissionForm(participant_name="Test", week_number=0)

    def test_week_too_high(self):
        with pytest.raises(ValidationError):
            SubmissionForm(participant_name="Test", week_number=21)

    def test_week_boundaries_valid(self):
        form1 = SubmissionForm(participant_name="Test", week_number=1)
        form20 = SubmissionForm(participant_name="Test", week_number=20)
        assert form1.week_number == 1
        assert form20.week_number == 20

    def test_missing_participant_name(self):
        with pytest.raises(ValidationError):
            SubmissionForm(week_number=1)  # type: ignore[call-arg]

    def test_missing_week_number(self):
        with pytest.raises(ValidationError):
            SubmissionForm(participant_name="Test")  # type: ignore[call-arg]
