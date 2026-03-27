"""API package for Exercise Competition.

This package contains FastAPI routers and API-related functionality.
"""

from __future__ import annotations

from exercise_competition.api.health import router as health_router

__all__ = ["health_router"]
