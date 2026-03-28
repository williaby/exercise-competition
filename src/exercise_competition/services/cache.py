"""Simple in-memory TTL cache for leaderboard standings.

Avoids recalculating standings on every request. Cache is invalidated
after ``ttl_seconds`` or when ``invalidate()`` is called (e.g. after a new
submission).

This is intentionally minimal — no third-party dependencies. For production
with multiple workers, replace with Redis or similar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exercise_competition.services.scoring import Standing

_DEFAULT_TTL = 300  # 5 minutes


@dataclass
class _CacheEntry:
    """A cached list of standings with expiry timestamp."""

    standings: list[Standing]
    expires_at: float


@dataclass
class StandingsCache:
    """Thread-safe TTL cache for leaderboard standings.

    Attributes:
        ttl_seconds: How long cached data remains valid.
    """

    ttl_seconds: float = _DEFAULT_TTL
    _entry: _CacheEntry | None = field(default=None, init=False, repr=False)

    def get(self) -> list[Standing] | None:
        """Return cached standings if still valid, else None."""
        if self._entry is None:
            return None
        if time.time() > self._entry.expires_at:
            self._entry = None
            return None
        return self._entry.standings

    def set(self, standings: list[Standing]) -> None:
        """Store standings with a new expiry."""
        self._entry = _CacheEntry(
            standings=standings,
            expires_at=time.time() + self.ttl_seconds,
        )

    def invalidate(self) -> None:
        """Immediately expire the cache (e.g. after a new submission)."""
        self._entry = None


# Module-level singleton
standings_cache = StandingsCache()
