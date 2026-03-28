"""SQLAlchemy ORM models for the exercise competition."""

from __future__ import annotations

import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class Participant(Base):
    """A competition participant (one of the four brothers).

    Attributes:
        id: Auto-increment primary key.
        name: Unique participant name (e.g. "Byron Williams").
        created_at: Timestamp when the participant was added.
        submissions: Related weekly submissions.
    """

    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.now,
    )

    submissions: Mapped[list[WeeklySubmission]] = relationship(
        back_populates="participant",
    )

    def __repr__(self) -> str:
        return f"Participant(id={self.id}, name={self.name!r})"


class WeeklySubmission(Base):
    """A participant's exercise submission for a specific week.

    Each day field is True if the participant exercised 30+ minutes that day.
    Compliance: 2+ days checked = 1 point for the week.

    Attributes:
        id: Auto-increment primary key.
        participant_id: Foreign key to Participant.
        week_number: Competition week (1-20).
        monday: Exercised on Monday.
        tuesday: Exercised on Tuesday.
        wednesday: Exercised on Wednesday.
        thursday: Exercised on Thursday.
        friday: Exercised on Friday.
        saturday: Exercised on Saturday.
        sunday: Exercised on Sunday.
        created_at: Timestamp when the submission was created.
        participant: Related participant.
    """

    __tablename__ = "weekly_submissions"
    __table_args__ = (
        UniqueConstraint("participant_id", "week_number", name="uq_participant_week"),
        CheckConstraint("week_number >= 1 AND week_number <= 20", name="ck_week_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    monday: Mapped[bool] = mapped_column(Boolean, default=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, default=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, default=False)
    thursday: Mapped[bool] = mapped_column(Boolean, default=False)
    friday: Mapped[bool] = mapped_column(Boolean, default=False)
    saturday: Mapped[bool] = mapped_column(Boolean, default=False)
    sunday: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.now,
    )

    participant: Mapped[Participant] = relationship(back_populates="submissions")

    @property
    def days_exercised(self) -> int:
        """Count the number of days exercised this week."""
        return sum(
            [
                self.monday,
                self.tuesday,
                self.wednesday,
                self.thursday,
                self.friday,
                self.saturday,
                self.sunday,
            ]
        )

    @property
    def is_compliant(self) -> bool:
        """Whether this week meets the compliance threshold (2+ days)."""
        from exercise_competition.core.config import settings  # noqa: PLC0415

        return self.days_exercised >= settings.compliance_threshold

    def __repr__(self) -> str:
        return (
            f"WeeklySubmission(id={self.id}, "
            f"participant_id={self.participant_id}, "
            f"week={self.week_number}, "
            f"days={self.days_exercised})"
        )
