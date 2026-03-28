# ADR-001: Initial Architecture -- FastAPI + SQLite + Cloudflare Zero Trust

> **Status**: Accepted
> **Date**: 2026-03-27

## TL;DR

Use FastAPI with Jinja2 server-rendered templates and SQLite, deployed behind a Cloudflare Zero Trust tunnel on a small Vultr VPS. Authentication is handled entirely by Cloudflare -- no app-level auth needed.

## Context

### Problem

We need a web application architecture for a checkbox-based exercise tracker serving 4 users over 20 weeks. The app runs on a small Vultr instance behind a Cloudflare Zero Trust tunnel, so resource efficiency, deployment simplicity, and zero auth code are paramount.

### Constraints

- **Technical**: Small VPS (likely 1 CPU, 1-2 GB RAM), single-developer project, Python 3.12
- **Business**: Must be deployable within days. Minimal ongoing ops burden.
- **Network**: Cloudflare Zero Trust tunnel provides both HTTPS and access control

### Significance

This decision shapes every subsequent implementation choice. Over-engineering wastes time on a 4-user app. The Cloudflare tunnel eliminates an entire category of work (auth, HTTPS cert management).

## Decision

**We will use FastAPI with Jinja2 templates, SQLite, and Cloudflare Zero Trust because it eliminates auth code, provides free HTTPS, and is the simplest production-capable stack for a small VPS.**

### Rationale

- FastAPI provides async performance, automatic OpenAPI docs, and Pydantic validation out of the box
- Jinja2 server-side rendering avoids a separate frontend build step and JavaScript framework
- SQLite requires zero configuration, runs in-process, and handles the tiny write volume easily
- Cloudflare Zero Trust tunnel handles HTTPS termination and access control with zero app code
- Single Docker container deployment keeps ops trivial

## Options Considered

### Option 1: FastAPI + Jinja2 + SQLite + Cloudflare Zero Trust (Chosen)

**Pros**:

- Zero auth code needed -- Cloudflare handles access control
- Free HTTPS via Cloudflare -- no cert management
- Single container, ~50 MB image
- SQLite handles concurrent reads well; write volume is negligible (~4 writes/week)
- FastAPI's Pydantic models give free input validation

**Cons**:

- SQLite has limited concurrent write support (mitigated: WAL mode, single Uvicorn worker, negligible write volume)
- Server-rendered templates are less interactive than SPA (acceptable for checkbox form)

### Option 2: Flask + PostgreSQL + Self-managed Auth

**Pros**:

- Flask is well-known and simple
- PostgreSQL is battle-tested

**Cons**:

- PostgreSQL requires a separate process and ~100 MB+ RAM on a small VPS
- Would need to build auth layer (unnecessary with Cloudflare Zero Trust)
- Overkill for 4 users and ~4 writes/week

### Option 3: Static Site + API (e.g., HTMX or React)

**Pros**:

- Could serve static files from Cloudflare CDN

**Cons**:

- Still needs a backend API for data
- More complex deployment (two components)
- Unnecessary for a simple form + leaderboard

## Consequences

### Positive

- **Fast to build**: Two pages (form + leaderboard), one model layer, one database file
- **Zero auth work**: Cloudflare Zero Trust handles all access control
- **Free HTTPS**: No cert management, no Caddy/nginx config
- **Easy to deploy**: Single `docker compose up` on the Vultr instance (single Uvicorn worker for SQLite)
- **Low resource usage**: ~30-50 MB RAM at runtime
- **Easy to back up**: Copy one SQLite file

### Trade-offs

- **No real-time updates**: Leaderboard requires page refresh (acceptable for weekly competition)
- **Limited to single server**: No horizontal scaling (not needed for 4 users)
- **Cloudflare dependency**: Access control tied to Cloudflare account (acceptable -- already in use)

### Technical Debt

- If the competition grows or needs real-time features, consider PostgreSQL and HTMX

## Implementation

### Components Affected

1. **Web layer**: FastAPI app with Jinja2 templates in `src/exercise_competition/api/`
2. **Data layer**: SQLite via SQLAlchemy async in `src/exercise_competition/core/`
3. **Deployment**: Single Dockerfile, docker-compose.yml with volume for SQLite persistence
4. **Network**: Cloudflare Zero Trust tunnel -> Vultr VPS port 8000

### Testing Strategy

- Unit: Model validation, scoring logic (90%+ coverage on core)
- Integration: Form submission -> database -> leaderboard rendering
- E2E: Browser smoke test of submit + view flow

## Validation

### Success Criteria

- [ ] App starts and serves pages in < 2 seconds on Vultr instance
- [ ] Docker image < 100 MB
- [ ] Memory usage < 100 MB at runtime
- [ ] Cloudflare tunnel routes HTTPS traffic to app successfully

### Review Schedule

- Initial: After Phase 1 MVP deployment
- Ongoing: Mid-competition check (Week 10)

## Related

- [Project Vision](../project-vision.md): Scope and constraints
- [Tech Spec](../tech-spec.md): Detailed implementation
