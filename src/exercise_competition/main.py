"""FastAPI application entry point for the exercise competition tracker."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from exercise_competition.api.health import router as health_router
from exercise_competition.api.routes import router as app_router
from exercise_competition.core.config import settings
from exercise_competition.core.database import init_db
from exercise_competition.middleware.correlation import CorrelationMiddleware
from exercise_competition.middleware.security import add_security_middleware
from exercise_competition.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize DB on startup."""
    setup_logging()
    logger.info("Starting exercise competition app")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down exercise competition app")


app = FastAPI(
    title="Exercise Competition",
    description="Weekly exercise competition tracker with leaderboard",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
# HTTPS redirect is disabled because Cloudflare Zero Trust terminates TLS.
# Traffic from Cloudflare to origin travels through a secure tunnel, so
# the origin only sees HTTP. Enabling redirect here would cause a loop.
add_security_middleware(
    app,
    enable_https_redirect=False,
    enable_rate_limiting=True,
    enable_ssrf_prevention=True,
    rate_limit_rpm=settings.rate_limit_rpm,
)
app.add_middleware(CorrelationMiddleware)

# Routers
app.include_router(health_router)
app.include_router(app_router)

# Static files and templates
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
