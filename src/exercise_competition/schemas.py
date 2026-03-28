"""Pydantic schemas for form validation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SubmissionForm(BaseModel):
    """Validates the weekly exercise submission form.

    Attributes:
        participant_name: Must match a known participant name.
        week_number: Competition week (1-20).
        monday: Exercised 30+ min on Monday.
        tuesday: Exercised 30+ min on Tuesday.
        wednesday: Exercised 30+ min on Wednesday.
        thursday: Exercised 30+ min on Thursday.
        friday: Exercised 30+ min on Friday.
        saturday: Exercised 30+ min on Saturday.
        sunday: Exercised 30+ min on Sunday.
    """

    participant_name: str
    week_number: int = Field(ge=1, le=20)
    monday: bool = False
    tuesday: bool = False
    wednesday: bool = False
    thursday: bool = False
    friday: bool = False
    saturday: bool = False
    sunday: bool = False
