# Multi-stage Dockerfile for Exercise Competition
# Optimized for production with security best practices and minimal image size

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.12.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12.13-slim

LABEL org.opencontainers.image.title="Exercise Competition"
LABEL org.opencontainers.image.description="Weekly exercise competition tracker with leaderboard"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="Byron Williams <byron@example.com>"
LABEL org.opencontainers.image.url="https://github.com/ByronWilliamsCPA/exercise-competition"
LABEL org.opencontainers.image.source="https://github.com/ByronWilliamsCPA/exercise-competition"
LABEL org.opencontainers.image.licenses="MIT"

# Install curl for healthcheck, create non-root user, then clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directory for SQLite and remove pip/setuptools from runtime image
RUN mkdir -p /app/data && chown appuser:appuser /app/data \
    && (pip uninstall -y pip setuptools 2>/dev/null || true)

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    EXERCISE_COMPETITION_DATABASE_URL="sqlite:////app/data/competition.db"

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "exercise_competition.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "10"]
