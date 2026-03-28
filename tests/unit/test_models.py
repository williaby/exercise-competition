"""Unit tests for SQLAlchemy models."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from exercise_competition.models import Base, Participant, WeeklySubmission


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_session(db_session):
    """Session with 4 participants pre-seeded."""
    names = [
        "Byron Williams",
        "Justin Williams",
        "Nick Williams",
        "Bruce Williams",
    ]
    for name in names:
        db_session.add(Participant(name=name))
    db_session.commit()
    return db_session


class TestParticipant:
    """Tests for the Participant model."""

    def test_create_participant(self, db_session):
        p = Participant(name="Test User")
        db_session.add(p)
        db_session.commit()

        result = db_session.query(Participant).first()
        assert result is not None
        assert result.name == "Test User"
        assert result.id is not None
        assert result.created_at is not None

    def test_participant_name_unique(self, db_session):
        db_session.add(Participant(name="Byron Williams"))
        db_session.commit()

        db_session.add(Participant(name="Byron Williams"))
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_participant_repr(self, db_session):
        p = Participant(name="Byron Williams")
        db_session.add(p)
        db_session.commit()

        assert "Byron Williams" in repr(p)
        assert "Participant" in repr(p)

    def test_participant_submissions_relationship(self, seeded_session):
        participant = seeded_session.query(Participant).filter_by(
            name="Byron Williams"
        ).first()
        assert participant is not None
        assert participant.submissions == []


class TestWeeklySubmission:
    """Tests for the WeeklySubmission model."""

    def test_create_submission(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
            wednesday=True,
            friday=True,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        result = seeded_session.query(WeeklySubmission).first()
        assert result is not None
        assert result.week_number == 1
        assert result.monday is True
        assert result.tuesday is False
        assert result.wednesday is True
        assert result.friday is True
        assert result.saturday is False

    def test_days_default_to_false(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        result = seeded_session.query(WeeklySubmission).first()
        assert result.monday is False
        assert result.tuesday is False
        assert result.wednesday is False
        assert result.thursday is False
        assert result.friday is False
        assert result.saturday is False
        assert result.sunday is False

    def test_days_exercised_count(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
            wednesday=True,
            friday=True,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        assert sub.days_exercised == 3

    def test_days_exercised_zero(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        assert sub.days_exercised == 0

    def test_is_compliant_true(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
            tuesday=True,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        assert sub.is_compliant is True

    def test_is_compliant_false_one_day(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        assert sub.is_compliant is False

    def test_is_compliant_false_zero_days(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        assert sub.is_compliant is False

    def test_unique_constraint_participant_week(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub1 = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
        )
        seeded_session.add(sub1)
        seeded_session.commit()

        sub2 = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            tuesday=True,
        )
        seeded_session.add(sub2)
        with pytest.raises(IntegrityError):
            seeded_session.commit()

    def test_different_participants_same_week(self, seeded_session):
        participants = seeded_session.query(Participant).all()
        sub1 = WeeklySubmission(
            participant_id=participants[0].id,
            week_number=1,
            monday=True,
        )
        sub2 = WeeklySubmission(
            participant_id=participants[1].id,
            week_number=1,
            tuesday=True,
        )
        seeded_session.add_all([sub1, sub2])
        seeded_session.commit()

        results = seeded_session.query(WeeklySubmission).all()
        assert len(results) == 2

    def test_same_participant_different_weeks(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub1 = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
        )
        sub2 = WeeklySubmission(
            participant_id=participant.id,
            week_number=2,
            tuesday=True,
        )
        seeded_session.add_all([sub1, sub2])
        seeded_session.commit()

        results = seeded_session.query(WeeklySubmission).all()
        assert len(results) == 2

    def test_week_number_check_constraint_too_low(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=0,
        )
        seeded_session.add(sub)
        with pytest.raises(IntegrityError):
            seeded_session.commit()

    def test_week_number_check_constraint_too_high(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=21,
        )
        seeded_session.add(sub)
        with pytest.raises(IntegrityError):
            seeded_session.commit()

    def test_week_number_boundary_valid(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub1 = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
        )
        sub20 = WeeklySubmission(
            participant_id=participant.id,
            week_number=20,
        )
        seeded_session.add_all([sub1, sub20])
        seeded_session.commit()

        results = seeded_session.query(WeeklySubmission).all()
        assert len(results) == 2

    def test_submission_repr(self, seeded_session):
        participant = seeded_session.query(Participant).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=3,
            monday=True,
            friday=True,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        r = repr(sub)
        assert "WeeklySubmission" in r
        assert "week=3" in r
        assert "days=2" in r

    def test_submission_relationship_to_participant(self, seeded_session):
        participant = seeded_session.query(Participant).filter_by(
            name="Byron Williams"
        ).first()
        sub = WeeklySubmission(
            participant_id=participant.id,
            week_number=1,
            monday=True,
        )
        seeded_session.add(sub)
        seeded_session.commit()

        # Refresh to load relationship
        seeded_session.refresh(sub)
        assert sub.participant.name == "Byron Williams"
        assert len(participant.submissions) == 1


class TestDatabaseInit:
    """Tests for database initialization and seeding."""

    def test_init_db_creates_tables_and_seeds(self):
        from exercise_competition.core.database import (
            get_engine,
            init_db,
            reset_engine,
        )
        from exercise_competition.core.config import Settings

        # Use a temp file for this test
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            # Monkey-patch settings
            import exercise_competition.core.database as db_module
            original_settings = db_module.settings
            db_module.settings = Settings(
                database_url=f"sqlite:///{db_path}",
            )
            try:
                reset_engine()
                init_db()

                engine = get_engine()
                with Session(engine) as session:
                    participants = session.query(Participant).all()
                    assert len(participants) == 4
                    names = {p.name for p in participants}
                    assert "Byron Williams" in names
                    assert "Justin Williams" in names
                    assert "Nick Williams" in names
                    assert "Bruce Williams" in names
            finally:
                reset_engine()
                db_module.settings = original_settings

    def test_init_db_idempotent(self):
        from exercise_competition.core.database import (
            get_engine,
            init_db,
            reset_engine,
        )
        from exercise_competition.core.config import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            import exercise_competition.core.database as db_module
            original_settings = db_module.settings
            db_module.settings = Settings(
                database_url=f"sqlite:///{db_path}",
            )
            try:
                reset_engine()
                init_db()
                init_db()  # Second call should be safe

                engine = get_engine()
                with Session(engine) as session:
                    participants = session.query(Participant).all()
                    assert len(participants) == 4  # Not 8
            finally:
                reset_engine()
                db_module.settings = original_settings
