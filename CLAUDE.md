# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Global development standards (code quality, security, git workflow, RAD tagging, supervisor role)
> are inherited from `~/.claude/CLAUDE.md`. This file covers **project-specific** context only.

## Template Feedback Requirement

This project was generated from [cookiecutter-python-template](https://github.com/ByronWilliamsCPA/cookiecutter-python-template) using cruft. When you find template issues (missing files, bad configs, doc gaps), add feedback to `docs/template_feedback.md` with: Issue, Context, Suggested Fix, Priority.

## Project Context

**What**: Weekly exercise competition tracker for 4 brothers (Byron, Justin, Nick, Bruce Williams).
20-week competition starting 2026-03-30. Participants check which days they exercised 30+ minutes;
2+ days/week = 1 point. Tiebreaker: average exercise days/week.

**Architecture**: FastAPI + SQLite + server-rendered Jinja2 templates. No app-level auth — Cloudflare
Zero Trust tunnel handles authentication (if you can reach the page, you're authorized). Deployed to
Vultr VPS via Docker. Single Uvicorn worker (SQLite constraint).

**ADR**: See `docs/planning/adr/adr-001-initial-architecture.md` for rationale.

## Development Status

**Current phase**: Foundation (Phase 0). Infrastructure code exists (exceptions, middleware, health
endpoints, logging). Next: SQLAlchemy models, database init, FastAPI main app, submission form,
leaderboard, scoring logic.

**Planning docs**: `docs/planning/PROJECT-PLAN.md` (master plan), `tech-spec.md`, `roadmap.md`,
`project-vision.md`.

## Build & Run Commands

```bash
# Setup
uv sync --all-extras
uv run pre-commit install

# Run tests (unit + integration; e2e excluded by default)
uv run pytest -v                                    # unit + integration
uv run pytest tests/unit/test_exceptions.py -v      # single file
uv run pytest -k "test_function_name" -v            # single test
uv run pytest --cov=src --cov-report=term-missing   # with coverage

# E2E tests (Playwright — requires: uv run playwright install chromium)
uv run pytest --run-e2e -v                          # all tests including E2E
uv run pytest tests/e2e/ -v --no-cov               # E2E only (separate session)

# Code quality
uv run ruff format .              # format
uv run ruff check . --fix         # lint + autofix
uv run basedpyright src/          # type check (strict mode)

# Security
uv run bandit -r src
uv run pip-audit

# Pre-commit (run before committing)
pre-commit run --all-files

# Docker
docker-compose up -d              # dev
docker-compose -f docker-compose.prod.yml up -d  # prod (hardened)
```

## Architecture

```
src/exercise_competition/
├── core/
│   ├── config.py         # Pydantic Settings (env prefix: exercise_competition_)
│   └── exceptions.py     # Full exception hierarchy (ValidationError, ResourceNotFoundError, etc.)
├── api/
│   └── health.py         # Kubernetes health probes (/health/live, /health/ready, /health/startup)
├── middleware/
│   ├── security.py       # Security headers, rate limiting, SSRF prevention
│   └── correlation.py    # Request correlation IDs (X-Correlation-ID, X-Request-ID)
└── utils/
    └── logging.py        # Structlog setup (JSON prod, Rich dev), correlation-aware
```

**Key patterns**:
- Config via Pydantic Settings with `.env` files and `exercise_competition_` env prefix
- Custom exceptions all have `to_dict()` for API responses
- Security middleware applied via `add_security_middleware(app)` helper
- Structured logging with automatic correlation ID injection

## Data Model (from tech-spec)

Two tables: `participants` (id, name, email) and `weekly_submissions` (participant_id, week_number,
days as JSON list of booleans, submitted_at). Scoring: count days with `True` >= 2 → 1 point for
that week.

## UX Design

Submission form: dropdown for participant name, week selector, 7 checkboxes (Mon-Sun) for days
exercised 30+ minutes. Append-only submissions — corrections done via direct DB access.

Leaderboard: shows all 20 weeks, points per participant, tiebreaker stats.

## Tool Configuration

- **Ruff**: 88 char lines, PyStrict-aligned rules, Google-style docstrings
- **BasedPyright**: strict mode in `pyproject.toml`
- **pytest**: 80% minimum coverage enforced, custom markers (unit, integration, security, perf)
- **Pre-commit**: Ruff, Bandit, TruffleHog, darglint, interrogate, conventional commits

## CI/CD

GitHub Actions workflows in `.github/workflows/`: CI (tests + lint), security analysis (CodeQL,
Bandit, OSV), container security (Trivy), SBOM generation, semantic release, FIPS compatibility.

## Cruft Template Updates

```bash
cruft check                    # check for updates
cruft update --skip CLAUDE.md --skip REUSE.toml --skip docs/template_feedback.md
# Then merge baseline changes: /merge-standards
```

## Frontend

React + TypeScript app in `frontend/` (Vite-based, npm). Separate Dockerfile. Not yet built out —
current plan uses server-rendered Jinja2 templates first.

## Branch Workflow

Never work on `main` directly. Create `feat/`, `fix/`, `docs/`, etc. branches. Use conventional
commits. Primary branch: `main`.
