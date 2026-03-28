"""SQLAlchemy ORM models for the exercise competition."""

from __future__ import annotations

import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
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
        """Whether this week meets the configured compliance threshold."""
        from exercise_competition.core.config import settings  # noqa: PLC0415

        return self.days_exercised >= settings.compliance_threshold

    def __repr__(self) -> str:
        return (
            f"WeeklySubmission(id={self.id}, "
            f"participant_id={self.participant_id}, "
            f"week={self.week_number}, "
            f"days={self.days_exercised})"
        )


class StravaToken(Base):
    """OAuth tokens for a participant's Strava connection.

    Stores the access/refresh tokens needed to fetch activities from Strava
    on behalf of a participant.

    Attributes:
        id: Auto-increment primary key.
        participant_id: Foreign key to Participant (unique — one Strava account per person).
        strava_athlete_id: Strava's unique athlete identifier.
        access_token: Current OAuth access token.
        refresh_token: OAuth refresh token (used to get new access tokens).
        expires_at: Unix timestamp when the access token expires.
        scope: OAuth scope granted (e.g. "activity:read").
        created_at: When the connection was first established.
        updated_at: When tokens were last refreshed.
    """

    __tablename__ = "strava_tokens"
    __table_args__ = (
        UniqueConstraint("participant_id", name="uq_strava_participant"),
        UniqueConstraint("strava_athlete_id", name="uq_strava_athlete"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )
    strava_athlete_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    access_token: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str] = mapped_column(String(100), default="activity:read")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now
    )

    participant: Mapped[Participant] = relationship()

    @property
    def is_expired(self) -> bool:
        """Whether the access token has expired."""
        import time  # noqa: PLC0415

        return int(time.time()) >= self.expires_at

    def __repr__(self) -> str:
        return (
            f"StravaToken(id={self.id}, "
            f"participant_id={self.participant_id}, "
            f"athlete={self.strava_athlete_id})"
        )


class StravaActivity(Base):
    """A Strava activity synced for a participant.

    Stores individual activities fetched from Strava, used to auto-fill
    weekly submission day checkboxes.

    Attributes:
        id: Auto-increment primary key.
        participant_id: Foreign key to Participant.
        strava_activity_id: Strava's unique activity identifier.
        activity_type: Strava activity type (Run, Ride, Swim, etc.).
        name: Activity name from Strava.
        start_date_local: Local start time of the activity.
        elapsed_time_seconds: Total elapsed time in seconds.
        moving_time_seconds: Moving time in seconds.
        distance_meters: Distance in meters (nullable for gym activities).
        created_at: When this record was synced.
    """

    __tablename__ = "strava_activities"
    __table_args__ = (
        UniqueConstraint("strava_activity_id", name="uq_strava_activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )
    strava_activity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date_local: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    elapsed_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    moving_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )

    participant: Mapped[Participant] = relationship()

    @property
    def duration_minutes(self) -> float:
        """Activity duration in minutes (using moving time)."""
        return self.moving_time_seconds / 60.0

    def __repr__(self) -> str:
        return (
            f"StravaActivity(id={self.id}, "
            f"participant_id={self.participant_id}, "
            f"type={self.activity_type!r}, "
            f"mins={self.duration_minutes:.0f})"
        )
