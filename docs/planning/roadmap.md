# Development Roadmap: Exercise Competition

> **Status**: Active | **Updated**: 2026-03-27

## TL;DR

Build a checkbox-based weekly exercise competition tracker in 3 phases over ~1 week, targeting deployment before the first week's submissions are due (2026-04-06, end of Week 1).

## Timeline Overview

```text
Phase 0: Foundation    ████████░░░░░░░░ (1 day)   - Models, DB, app skeleton
Phase 1: MVP Core      ░░░░████████████ (2-3 days) - Form, leaderboard, scoring
Phase 2: Deploy        ░░░░░░░░░░░░████ (1 day)   - Docker, Cloudflare tunnel
```

## Milestones

| Milestone | Target | Status | Dependencies |
| --------- | ------ | ------ | ------------ |
| M0: Dev Environment Ready | 2026-03-28 | Planned | None |
| M1: Form + Leaderboard Working | 2026-03-31 | Planned | M0 |
| M2: Deployed via Cloudflare Tunnel | 2026-04-02 | Planned | M1 |

---

## Phase 0: Foundation (Day 1)

### Objective

Database models, seed data, project dependencies, and FastAPI skeleton ready.

### Deliverables

- [ ] SQLAlchemy models for `Participant` and `WeeklySubmission`
- [ ] Database init via `metadata.create_all()` (Alembic deferred to post-MVP)
- [ ] Seed data: 4 participants (Byron, Justin, Nick, Bruce Williams)
- [ ] FastAPI app skeleton with health check endpoint
- [ ] Pre-commit hooks working
- [ ] CI workflows referencing org reusable workflows
- [ ] Dependabot configuration

### Success Criteria

- `uv run pytest` passes with models tested
- `uv run uvicorn exercise_competition.api.main:app` starts and returns 200 on `/health`
- Pre-commit hooks pass
- CI pipeline runs on push/PR

### Tasks

| Task | Est. Hours | Status |
| ---- | ---------- | ------ |
| Add FastAPI, SQLAlchemy, aiosqlite, Jinja2 dependencies | 1 | Planned |
| Create SQLAlchemy models (Participant, WeeklySubmission) | 2 | Planned |
| Database init via create_all() with seed data | 1 | Planned |
| FastAPI app skeleton with health endpoint | 1 | Planned |
| Configure CI via org reusable workflows (python-ci, python-security-analysis) | 0.5 | Planned |
| Add dependabot.yml (pip, Docker, GitHub Actions) | 0.25 | Planned |
| Unit tests for models | 1 | Planned |

### Git Branch

`feat/phase-0-foundation`

---

## Phase 1: MVP Core (Days 2-4)

### Objective

Working checkbox submission form, compliance scoring, and leaderboard page.

### Deliverables

- [ ] Checkbox-based weekly submission form (name dropdown, week selector, day checkboxes)
- [ ] Compliance scoring service (1 point for 2+ days checked)
- [ ] Leaderboard page with cumulative standings and tiebreaker
- [ ] Per-week results view

### Success Criteria

- Submit a week via the checkbox form and see it reflected on the leaderboard
- Compliance correctly awards 1 point for weeks with 2+ days
- Leaderboard ranks by points, then average days/week as tiebreaker
- Duplicate submissions (same participant + week) are rejected

### User Stories

#### US-001: Submit Weekly Exercise

**As a** participant
**I want** to check off which days I exercised this week
**So that** my weekly score is recorded in the competition

**Acceptance Criteria**:

- [ ] Form shows dropdown of 4 participant names
- [ ] Week selector shows weeks 1-20 with current week pre-selected
- [ ] 7 checkboxes (Mon-Sun) for marking exercise days
- [ ] Success message shown after submission via query-param redirect
- [ ] Duplicate (same person + week) shows error, not silent overwrite

**Tasks**:

| Task | Est. Hours | Status |
| ---- | ---------- | ------ |
| Create Jinja2 submit form template with checkboxes | 2 | Planned |
| Implement POST /submit route with Pydantic validation | 2 | Planned |
| Add duplicate-submission detection | 1 | Planned |
| Client-side helpers (current week pre-select) | 0.5 | Planned |

#### US-002: View Leaderboard

**As a** participant
**I want** to see the overall standings
**So that** I know who is winning the competition

**Acceptance Criteria**:

- [ ] Shows all 4 participants ranked by points (compliant weeks)
- [ ] Displays average exercise days/week as tiebreaker
- [ ] Shows current streak of compliant weeks
- [ ] Updates immediately after new submissions

**Tasks**:

| Task | Est. Hours | Status |
| ---- | ---------- | ------ |
| Implement scoring/compliance service | 2 | Planned |
| Create leaderboard template | 2 | Planned |
| Implement GET /leaderboard route | 1 | Planned |
| Create GET /week/{n} route and template | 1.5 | Planned |
| Integration tests for submit -> leaderboard flow | 2 | Planned |

### Dependencies

- Requires: Phase 0 complete
- Blocks: Phase 2

### Git Branch

`feat/phase-1-mvp-core`

---

## Phase 2: Deploy (Day 5)

### Objective

Dockerized deployment on Vultr behind Cloudflare Zero Trust tunnel, mobile-friendly styling.

### Deliverables

- [ ] Hardened Dockerfile (multi-stage, pinned base, non-root user, pip removed)
- [ ] Hardened docker-compose.yml (read-only FS, cap_drop ALL, no-new-privileges, resource limits, tmpfs, log limits, healthcheck)
- [ ] .dockerignore file
- [ ] Deployed and accessible via Cloudflare Zero Trust tunnel (HTTPS)
- [ ] Responsive CSS for mobile checkbox form
- [ ] Container security workflow passes (Trivy, no HIGH/CRITICAL)
- [ ] Test coverage >= 80%

### Success Criteria

- App running on Vultr, accessible via Cloudflare tunnel URL
- Checkbox form usable on mobile phone screens
- All tests pass, coverage >= 80%
- SQLite data persists across container restarts

### Tasks

| Task | Est. Hours | Status |
| ---- | ---------- | ------ |
| Write hardened Dockerfile (multi-stage, pinned base, non-root user, pip removed) | 1.5 | Planned |
| Create hardened docker-compose.yml (read-only, cap_drop, mem/cpu/pid limits, tmpfs, log limits) | 1 | Planned |
| Add .dockerignore (.env, .git/, tests/, __pycache__/) | 0.25 | Planned |
| Add HEALTHCHECK on /health endpoint | 0.25 | Planned |
| Add responsive CSS / minimal styling | 2 | Planned |
| Configure Cloudflare Zero Trust tunnel to Vultr | 1 | Planned |
| Smoke test from mobile device via tunnel | 0.5 | Planned |
| Enable python-container-security.yml workflow (Trivy scan) | 0.5 | Planned |
| Increase test coverage to 80%+ | 2 | Planned |
| Set up SQLite backup cron | 0.5 | Planned |

### Git Branch

`feat/phase-2-deploy`

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
| ---- | ----------- | ------ | ---------- |
| Vultr instance too small for Docker | L | H | Test image size locally; use slim base image |
| Brothers lose interest after a few weeks | M | M | Keep UX frictionless (checkboxes, not duration entry) |
| SQLite corruption from abrupt shutdown | L | M | WAL mode + weekly backups |
| Cloudflare tunnel configuration issues | L | M | Test tunnel locally first; fallback to direct access |
| Competition rules need mid-stream changes | M | L | Scoring logic isolated in single service module |

## Definition of Done

A feature is complete when:

- [ ] Tests written and passing
- [ ] No linting or type-check errors
- [ ] Works on mobile viewport
- [ ] Merged to main via PR

## Related Documents

- [Project Vision](./project-vision.md)
- [Technical Spec](./tech-spec.md)
- [Architecture Decisions](./adr/)
