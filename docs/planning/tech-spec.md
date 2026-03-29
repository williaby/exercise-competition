# Technical Implementation Spec: Exercise Competition

> **Status**: Draft | **Version**: 1.1 | **Updated**: 2026-03-27

## TL;DR

A FastAPI + Jinja2 + SQLite monolith serving a checkbox-based weekly submission form and leaderboard for 4 participants. No app-level auth (Cloudflare Zero Trust). HTTPS via Cloudflare. Deployed as a single Docker container on a small Vultr VPS.

## Technology Stack

### Core

- **Language**: Python 3.12
- **Package Manager**: UV
- **Framework**: FastAPI 0.115+ with Jinja2 templates
- **ASGI Server**: Uvicorn (single worker for SQLite compatibility)

### Code Quality

- **Linter/Formatter**: Ruff (88 chars)
- **Type Checker**: BasedPyright (strict)
- **Testing**: pytest + coverage

### Data Layer

- **Database**: SQLite 3 (WAL mode) -- See [ADR-001](./adr/adr-001-initial-architecture.md)
- **ORM**: SQLAlchemy 2.0 (async via aiosqlite)
- **Migrations**: `metadata.create_all()` for MVP (Alembic deferred)

### Infrastructure

- **CI/CD**: GitHub Actions using org reusable workflows from `ByronWilliamsCPA/.github`
- **Container**: Docker + docker-compose
- **Hosting**: Vultr VPS behind Cloudflare Zero Trust tunnel
- **HTTPS**: Cloudflare/Zero Trust SSL (no self-managed certs)
- **Dependency Management**: Dependabot (pip, Docker, GitHub Actions ecosystems)

## Architecture

### Pattern

Server-rendered monolith -- See [ADR-001](./adr/adr-001-initial-architecture.md)

### Component Diagram

```text
┌──────────────────────────────────────────────┐
│         Cloudflare Zero Trust Tunnel         │
│         (HTTPS + Access Control)             │
└──────────────────┬───────────────────────────┘
                   │ HTTP :8000
┌──────────────────▼───────────────────────────┐
│              FastAPI Application              │
├──────────────┬──────────────┬────────────────┤
│  Routes      │  Templates   │  Static Files  │
│  (form,      │  (Jinja2     │  (CSS)         │
│   leaderboard│   HTML)      │                │
│   week view) │              │                │
└──────┬───────┴──────────────┴────────────────┘
       │
       ▼
┌──────────────────────┐
│   Service Layer      │
│  (scoring, week calc,│
│   compliance logic)  │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   SQLAlchemy Models  │
│   + SQLite (WAL)     │
└──────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Key Functions |
| --------- | ------- | ------------- |
| Routes | HTTP endpoints for form and views | `submit_week`, `view_leaderboard`, `view_week` |
| Service | Business logic | `calculate_compliance`, `compute_standings`, `get_week_number` |
| Models | Data persistence | `Participant`, `WeeklySubmission` |
| Templates | HTML rendering | `submit.html`, `leaderboard.html`, `week_results.html` |

## Data Model

### Core Entities

```python
class Participant:
    id: int  # auto-increment
    name: str  # unique, e.g. "Byron Williams"
    created_at: datetime

class WeeklySubmission:
    id: int
    participant_id: int  # FK -> Participant
    week_number: int  # 1-20
    monday: bool  # True if exercised 30+ min
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    created_at: datetime
    # Unique constraint: (participant_id, week_number)
```

### Derived (Computed at Query Time)

```python
# days_exercised: count of True day columns in a WeeklySubmission
# compliant: days_exercised >= 2
# points: count of compliant weeks per participant
# avg_days: total days_exercised / weeks_submitted (tiebreaker)
# streak: consecutive compliant weeks from most recent backward
```

### Relationships

- `Participant` -> `WeeklySubmission`: One-to-many (one submission per participant per week)

### Seed Data (4 Participants)

```python
PARTICIPANTS = [
    "Byron Williams",
    "Justin Williams",
    "Nick Williams",
    "Bruce Williams",
]
```

### Competition Rules (Encoded in Service Layer)

- **Competition period**: Week 1 starts Monday 2026-03-23, ends Sunday 2026-08-09 (20 weeks)
- **Week boundaries**: Monday 00:00 through Sunday 23:59
- **Weekly compliance**: 2+ days checked as exercised (each day = 30+ min, honor system)
- **Scoring**: 1 point per compliant week
- **Tiebreaker**: Average exercise days per week (total days / weeks submitted)
- **Submissions**: One per participant per week; append-only (no UI edits; backend DB fixes only)

## API / Routes

### Pages (Server-Rendered)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/` | Redirect to leaderboard |
| GET | `/submit` | Weekly submission form |
| POST | `/submit` | Process checkbox form submission |
| GET | `/leaderboard` | Overall standings for all 20 weeks |
| GET | `/week/{week_number}` | Results for a specific week |

### Form Fields (POST /submit)

| Field | Type | Validation |
| ----- | ---- | ---------- |
| `participant_name` | select dropdown | Required, must match known participant |
| `week_number` | select dropdown | Required, 1-20, within competition period |
| `monday` | checkbox | Optional boolean |
| `tuesday` | checkbox | Optional boolean |
| `wednesday` | checkbox | Optional boolean |
| `thursday` | checkbox | Optional boolean |
| `friday` | checkbox | Optional boolean |
| `saturday` | checkbox | Optional boolean |
| `sunday` | checkbox | Optional boolean |

### Response Behavior

- Successful submission: redirect to `/leaderboard?msg=success` (query-param flash message)
- Duplicate submission (same participant + week): re-render form with error
- Validation error: re-render form with error messages and preserved input

## Security

### Authentication / Authorization

None at the application level. Cloudflare Zero Trust tunnel ensures only authorized users can reach the app. If you can access the page, you are authorized to use it.

### Network Security

- Cloudflare Zero Trust tunnel terminates HTTPS and enforces access policies
- Vultr instance firewall: allow only Cloudflare tunnel traffic (no direct public access)
- App listens on HTTP :8000 internally (Cloudflare handles TLS)

### Input Validation

- All form inputs validated via Pydantic models
- SQL injection prevented by SQLAlchemy parameterized queries
- XSS prevented by Jinja2 auto-escaping
- Unique constraint prevents duplicate week submissions

### Data Protection

- **At Rest**: SQLite file on Docker volume (no sensitive data beyond first names)
- **In Transit**: HTTPS via Cloudflare Zero Trust SSL
- **Backups**: Weekly cron copying SQLite file
- **Deployment**: Single Uvicorn worker (required for SQLite WAL mode consistency)

### Container Hardening (per DOCKER-HARDENING.md standards)

Applicable requirements from the org Docker hardening standards:

**Runtime Isolation (docker-compose.yml)**:

- R-01: `read_only: true` with tmpfs for writable paths
- R-02: `cap_drop: [ALL]` (no elevated capabilities needed)
- R-03: `security_opt: [no-new-privileges:true]`
- R-04: `mem_limit: 256m` (lightweight app, 4 users)
- R-05: `cpus: 0.5`
- R-06: `pids_limit: 50`
- R-15: `tmpfs` for `/tmp` (size=32M,noexec,nosuid)

**Image Build Security (Dockerfile)**:

- R-09: Pin base image to minor version (`python:3.12.8-slim`)
- R-10: Multi-stage build (builder installs deps, runtime copies only needed files)
- R-11: Dependencies pinned via UV lockfile
- R-12: Remove pip/package managers in final image
- R-13: OCI LABEL metadata (source, description, maintainer)
- R-14: COPY before USER switch for clean layer ownership

**Filesystem & Data**:

- R-16: SQLite volume is writable; no other writable mounts needed
- R-17: No secrets in env vars at build time (no secrets exist for this app)
- R-25: `.dockerignore` excludes `.env`, `.git/`, `tests/`, `__pycache__/`

**Logging & Observability**:

- R-21: `logging.driver: json-file` with `max-size: 10m`, `max-file: 3`
- R-22: `HEALTHCHECK` on `/health` endpoint

**Supply Chain**:

- R-24: `trivy image` scan in CI pipeline

**Not Applicable**: R-07 (no host network), R-08 (not ephemeral), R-18 (no published ports -- Cloudflare tunnel), R-19/R-20 (Tor-specific), R-23 (using official Python image)

**Reference docker-compose.yml pattern**:

```yaml
services:
  app:
    build: .
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    mem_limit: 256m
    cpus: 0.5
    pids_limit: 50
    tmpfs:
      - /tmp:size=32M,noexec,nosuid
    volumes:
      - app-data:/app/data  # SQLite persistence
    expose:
      - "8000"  # Internal only, Cloudflare tunnel connects
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

volumes:
  app-data:
```

**Reference Dockerfile pattern**:

```dockerfile
# ---- Builder stage ----
FROM python:3.12.8-slim AS builder
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

# ---- Runtime stage ----
FROM python:3.12.8-slim
LABEL org.opencontainers.image.source="https://github.com/ByronWilliamsCPA/exercise-competition"
LABEL org.opencontainers.image.description="Exercise Competition Tracker"
LABEL maintainer="Byron Williams"

COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/
RUN useradd -m -s /usr/sbin/nologin appuser \
    && rm -rf /root/.cache /usr/lib/python*/ensurepip /usr/lib/python*/pip*
USER appuser
WORKDIR /app
EXPOSE 8000
HEALTHCHECK CMD ["curl", "-f", "http://localhost:8000/health"]
ENTRYPOINT ["/app/.venv/bin/uvicorn", "exercise_competition.api.main:app", \
            "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

## CI/CD Pipeline (Org Reusable Workflows)

Uses reusable workflows from `ByronWilliamsCPA/.github` for consistency across all org projects.

### Workflows to Enable

| Workflow | Purpose | Trigger |
| -------- | ------- | ------- |
| `python-ci.yml` | Testing, linting (Ruff), type checking (BasedPyright), coverage (80%) | PR, push to main |
| `python-security-analysis.yml` | CodeQL, Bandit, Safety, OSV Scanner, dependency review | PR, push to main |
| `python-container-security.yml` | Docker image vulnerability scanning (Trivy) | PR with Dockerfile changes |
| `python-docker.yml` | Docker image build verification | PR with Dockerfile changes |

### Workflow Configuration

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  ci:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@main
    with:
      python-versions: '["3.12"]'
      coverage-threshold: 80
      source-directory: src
      test-directory: tests
    secrets: inherit
```

### Additional CI Standards (from org .github repo)

- **Dependabot**: Weekly Monday updates for pip, Docker, GitHub Actions
- **DCO sign-off**: Required on all commits (`git commit --signoff`)
- **PR template**: Org-standard template with quality checklist and DCO confirmation
- **Actions pinning**: All GitHub Actions pinned to commit SHAs (supply chain security)
- **CODEOWNERS**: `@williaby` as default reviewer

### Security Scanning (OWASP)

FastAPI triggers `owasp-web` + `owasp-api` specialist agents per org dispatch rules. Key focus areas:

- **A03 Injection**: SQLAlchemy parameterized queries (already addressed)
- **A05 Security Misconfiguration**: Docker hardening, Cloudflare tunnel config
- **A07 XSS**: Jinja2 auto-escaping (already addressed)

## Error Handling

### Strategy

Fail fast on invalid input, graceful error pages for users.

### Error Scenarios

| Scenario | Behavior |
| -------- | -------- |
| Invalid form input | Re-render form with validation messages |
| Duplicate submission | Re-render form with "already submitted for this week" message |
| Week out of range | 404 page |
| Database error | 500 page with generic message, log details |

### Logging

- **Format**: Structured logging via `exercise_competition.utils.logging`
- **Levels**: INFO for submissions, WARNING for validation failures, ERROR for exceptions
- **Sensitive**: No PII beyond first names

## Performance Requirements

| Metric | Target | Measurement |
| ------ | ------ | ----------- |
| Page load time | < 500ms | Server response time |
| Memory usage | < 100 MB | Docker stats |
| Docker image size | < 100 MB | `docker images` |
| Concurrent users | 4 | All brothers submitting simultaneously |

## Testing Strategy

### Coverage Target

- Minimum: 80% line coverage
- Critical paths (scoring, compliance): 95%+

### Test Types

- **Unit**: Scoring logic, compliance calculation, tiebreaker computation, Pydantic model validation
- **Integration**: Form submission -> database write -> leaderboard query
- **E2E**: Submit week via form, verify it appears on leaderboard with correct scoring

## Related Documents

- [Project Vision](./project-vision.md)
- [Architecture Decisions](./adr/)
- [Development Roadmap](./roadmap.md)
