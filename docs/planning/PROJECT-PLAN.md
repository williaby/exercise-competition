---
schema_type: planning
title: "Exercise Competition - Project Plan"
description: "Comprehensive project plan synthesized from planning documents"
status: active
generated: "2026-03-27"
source_documents:
  - project-vision.md
  - tech-spec.md
  - roadmap.md
  - adr/adr-001-initial-architecture.md
---

# Project Plan: Exercise Competition

> **Generated**: 2026-03-27
> **Status**: Ready for Development
> **Deadline**: Usable by 2026-04-06 (end of Week 1)

## Executive Summary

A dead-simple web app where four brothers (Byron, Justin, Nick, Bruce Williams) check off which days they exercised each week and compete on a 20-week leaderboard. FastAPI + Jinja2 + SQLite monolith, deployed as a single Docker container on a Vultr VPS behind Cloudflare Zero Trust (no app-level auth, free HTTPS). Competition starts week of 2026-03-23.

## Project Scope

### In Scope

- Checkbox-based weekly submission form (pick name, select week, check days exercised)
- Compliance scoring: 1 point per week with 2+ days of 30+ minute exercise
- Tiebreaker: average exercise days per week
- Leaderboard with cumulative standings across all 20 weeks
- Per-week results view showing each participant's checked days
- Mobile-friendly responsive design
- Dockerized deployment on Vultr VPS behind Cloudflare Zero Trust tunnel

### Out of Scope

- Login system (Cloudflare Zero Trust handles access)
- Admin page (data corrections via backend DB)
- Native mobile app, social features, exercise verification
- Notifications/reminders
- Historical competitions beyond current 20-week run

## Git Branch Strategy

| Phase | Branch | Type | Version Impact |
|-------|--------|------|----------------|
| Phase 0: Foundation | `feat/phase-0-foundation` | feat | Minor |
| Phase 1: MVP Core | `feat/phase-1-mvp-core` | feat | Minor |
| Phase 2: Deploy | `feat/phase-2-deploy` | feat | Minor |

**Start a phase**:
```bash
git checkout main && git pull origin main
git checkout -b feat/phase-{n}-{slug}
```

**Complete a phase**:
```bash
# Ensure all checks pass
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check .
uv run basedpyright src/
pre-commit run --all-files

# Create PR
```

## Phased Development

### Phase 0: Foundation (Day 1 — Target: 2026-03-28)

**Branch**: `feat/phase-0-foundation`
**Duration**: 1 day
**Dependencies**: None

**Deliverables**:

- SQLAlchemy models for `Participant` and `WeeklySubmission`
- Database init via `metadata.create_all()` (Alembic deferred)
- Seed data: 4 participants (Byron, Justin, Nick, Bruce Williams)
- FastAPI app skeleton with `/health` endpoint
- Pre-commit hooks working
- CI workflows referencing org reusable workflows (`python-ci.yml`, `python-security-analysis.yml`)
- Dependabot configuration (pip, Docker, GitHub Actions)

**Success Criteria**:

- `uv run pytest` passes with models tested
- `uv run uvicorn exercise_competition.api.main:app` starts, returns 200 on `/health`
- Pre-commit hooks pass
- CI pipeline runs on push/PR

**Tasks**:

| Task | Est. Hours |
| ---- | ---------- |
| Add FastAPI, SQLAlchemy, aiosqlite, Jinja2 dependencies | 1 |
| Create SQLAlchemy models (Participant, WeeklySubmission) | 2 |
| Database init via create_all() with seed data | 1 |
| FastAPI app skeleton with health endpoint | 1 |
| Configure CI via org reusable workflows | 0.5 |
| Add dependabot.yml | 0.25 |
| Unit tests for models | 1 |

---

### Phase 1: MVP Core (Days 2-4 — Target: 2026-03-31)

**Branch**: `feat/phase-1-mvp-core`
**Duration**: 2-3 days
**Dependencies**: Phase 0 complete

**Deliverables**:

- Checkbox-based weekly submission form (name dropdown, week selector, day checkboxes)
- Compliance scoring service (1 point for 2+ days checked)
- Leaderboard page with cumulative standings and tiebreaker
- Per-week results view

**Success Criteria**:

- Submit a week via the checkbox form and see it reflected on the leaderboard
- Compliance correctly awards 1 point for weeks with 2+ days
- Leaderboard ranks by points, then average days/week as tiebreaker
- Duplicate submissions (same participant + week) are rejected

**User Stories**:

**US-001: Submit Weekly Exercise**
- Form shows dropdown of 4 participant names
- Week selector shows weeks 1-20 with current week pre-selected
- 7 checkboxes (Mon-Sun) for marking exercise days
- Success message shown after submission via query-param redirect
- Duplicate (same person + week) shows error

**US-002: View Leaderboard**
- All 4 participants ranked by points (compliant weeks)
- Average exercise days/week displayed as tiebreaker
- Current streak of compliant weeks shown
- Updates immediately after new submissions

**Tasks**:

| Task | Est. Hours |
| ---- | ---------- |
| Create Jinja2 submit form template with checkboxes | 2 |
| Implement POST /submit route with Pydantic validation | 2 |
| Add duplicate-submission detection | 1 |
| Client-side helpers (current week pre-select) | 0.5 |
| Implement scoring/compliance service | 2 |
| Create leaderboard template | 2 |
| Implement GET /leaderboard route | 1 |
| Create GET /week/{n} route and template | 1.5 |
| Integration tests for submit -> leaderboard flow | 2 |

---

### Phase 2: Deploy (Day 5 — Target: 2026-04-02)

**Branch**: `feat/phase-2-deploy`
**Duration**: 1 day
**Dependencies**: Phase 1 complete

**Deliverables**:

- Hardened Dockerfile (multi-stage, pinned base, non-root user, pip removed)
- Hardened docker-compose.yml (read-only FS, cap_drop ALL, no-new-privileges, resource limits, tmpfs, log limits, healthcheck)
- .dockerignore file
- Deployed and accessible via Cloudflare Zero Trust tunnel (HTTPS)
- Responsive CSS for mobile checkbox form
- Container security workflow passes (Trivy, no HIGH/CRITICAL)
- Test coverage >= 80%

**Success Criteria**:

- App running on Vultr, accessible via Cloudflare tunnel URL
- Checkbox form usable on mobile phone screens
- All tests pass, coverage >= 80%
- SQLite data persists across container restarts

**Tasks**:

| Task | Est. Hours |
| ---- | ---------- |
| Write hardened Dockerfile | 1.5 |
| Create hardened docker-compose.yml | 1 |
| Add .dockerignore | 0.25 |
| Add HEALTHCHECK on /health | 0.25 |
| Add responsive CSS / minimal styling | 2 |
| Configure Cloudflare Zero Trust tunnel to Vultr | 1 |
| Smoke test from mobile device via tunnel | 0.5 |
| Enable python-container-security.yml workflow (Trivy) | 0.5 |
| Increase test coverage to 80%+ | 2 |
| Set up SQLite backup cron | 0.5 |

---

## System Architecture

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

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.12 |
| Package Manager | UV | Latest |
| Framework | FastAPI | 0.115+ |
| Templates | Jinja2 | Latest |
| ASGI Server | Uvicorn | Latest (1 worker) |
| ORM | SQLAlchemy | 2.0 (async via aiosqlite) |
| Database | SQLite 3 | WAL mode |
| Linter/Formatter | Ruff | 88 chars |
| Type Checker | BasedPyright | Strict mode |
| Testing | pytest + coverage | 80% minimum |
| Container | Docker + docker-compose | Multi-stage build |
| CI/CD | GitHub Actions | Org reusable workflows |
| Network | Cloudflare Zero Trust | Tunnel + HTTPS |

## Architecture Decisions

### ADR-001: FastAPI + SQLite + Cloudflare Zero Trust

**Status**: Accepted
**Summary**: Use FastAPI with Jinja2 server-rendered templates and SQLite, deployed behind a Cloudflare Zero Trust tunnel. No app-level auth needed.
**Rationale**: Zero auth code, free HTTPS, single-container deploy, ~30-50 MB RAM at runtime. SQLite handles the negligible write volume (~4 writes/week) easily. Cloudflare eliminates entire categories of work (auth, certs).

[Full ADR](./adr/adr-001-initial-architecture.md)

---

## Data Model

```python
class Participant:
    id: int              # auto-increment
    name: str            # unique, e.g. "Byron Williams"
    created_at: datetime

class WeeklySubmission:
    id: int
    participant_id: int  # FK -> Participant
    week_number: int     # 1-20
    monday: bool         # True if exercised 30+ min
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    created_at: datetime
    # Unique constraint: (participant_id, week_number)
```

**Competition Rules** (encoded in service layer):
- Week 1 starts Monday 2026-03-23, ends Sunday 2026-08-09 (20 weeks)
- Weekly compliance: 2+ days checked = 1 point
- Tiebreaker: average exercise days per week
- One submission per participant per week (append-only)

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Vultr instance too small for Docker | Low | High | Test image size locally; slim base image |
| Brothers lose interest after a few weeks | Medium | Medium | Frictionless UX (checkboxes, not duration entry) |
| SQLite corruption from abrupt shutdown | Low | Medium | WAL mode + weekly backups |
| Cloudflare tunnel configuration issues | Low | Medium | Test tunnel locally first; fallback to direct access |
| Competition rules need mid-stream changes | Medium | Low | Scoring logic isolated in single service module |

## Success Metrics

| Metric | Target |
|--------|--------|
| Participation rate | 90%+ weekly submissions across all 4 participants |
| Completion rate | Full 20 weeks without abandoning the tracker |
| Entry time | < 30 seconds to submit a week's exercise days |
| Page load time | < 500ms |
| Memory usage | < 100 MB |
| Docker image size | < 100 MB |

## Next Steps

1. Review this synthesized plan for accuracy
2. Start Phase 0:
   ```bash
   git checkout -b feat/phase-0-foundation
   ```
3. Track progress with TODO items per phase
4. Complete each phase with PR workflow

## Document References

- [Project Vision & Scope](./project-vision.md)
- [Technical Specification](./tech-spec.md)
- [Development Roadmap](./roadmap.md)
- [Architecture Decisions](./adr/)
