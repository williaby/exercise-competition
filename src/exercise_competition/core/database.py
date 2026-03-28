"""Database engine and session management for SQLite.

Uses synchronous SQLAlchemy with SQLite in WAL mode.
FastAPI runs sync endpoints in a threadpool automatically.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from exercise_competition.core.config import settings
from exercise_competition.models import Base, Participant

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.pool import ConnectionPoolEntry

SEED_PARTICIPANTS = [
    "Byron Williams",
    "Justin Williams",
    "Nick Williams",
    "Bruce Williams",
]

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _set_sqlite_wal(
    dbapi_connection: object,
    _connection_record: ConnectionPoolEntry,
) -> None:
    """Enable WAL mode and busy timeout on every new SQLite connection."""
    cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
    cursor.execute("PRAGMA journal_mode=WAL")  # NOSONAR(S2077) hardcoded SQLite PRAGMA, no user input
    cursor.execute("PRAGMA busy_timeout=5000")  # NOSONAR(S2077) hardcoded SQLite PRAGMA, no user input
    cursor.close()


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine.

    Returns:
        The configured SQLAlchemy engine.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        event.listen(_engine, "connect", _set_sqlite_wal)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or create the session factory.

    Returns:
        A sessionmaker bound to the engine.
    """
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session.

    Yields:
        A SQLAlchemy Session that auto-commits on success, rolls back on error.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables and seed participant data.

    Safe to call multiple times — only inserts seed data if the
    participants table is empty.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)

    with get_session() as session:
        existing = session.execute(text("SELECT COUNT(*) FROM participants")).scalar()  # NOSONAR(S2077) hardcoded seed check, no user input
        if existing == 0:
            for name in SEED_PARTICIPANTS:
                session.add(Participant(name=name))


def reset_engine() -> None:
    """Reset the engine and session factory. Used for testing."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
