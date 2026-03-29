# Project Vision & Scope: Exercise Competition

> **Status**: Active | **Version**: 1.1 | **Updated**: 2026-03-27

## TL;DR

A lightweight web app where four brothers (Byron, Justin, Nick, Bruce Williams) check off which days they exercised each week and compete on a 20-week leaderboard. Secured via Cloudflare Zero Trust tunnel, hosted on a small Vultr VPS.

## Problem Statement

### Pain Point

Tracking a family exercise competition manually (group chat, spreadsheets, honor system) leads to missed entries, disputed standings, and fading motivation after a few weeks. There is no single source of truth for who met the weekly minimums or who is leading overall.

### Target Users

- **Primary**: Byron, Justin, Nick, and Bruce Williams (4 brothers)
- **Context**: Weekly check-ins from phones or laptops; quick checkbox entry at end of week

### Success Metrics

- **Participation rate**: 0% -> 90%+ weekly submissions across all 4 participants
- **Completion rate**: Run full 20 weeks without abandoning the tracker
- **Entry time**: < 30 seconds to submit a week's exercise days

## Solution Overview

### Core Value

A dead-simple web form and leaderboard that makes the weekly competition visible, accountable, and fun without requiring any app installs or accounts.

### Key Capabilities (MVP)

1. **Weekly Checkbox Form**: Select name, pick week, check which days you hit 30+ minutes of exercise
2. **Automatic Compliance Check**: System awards 1 point for weeks with 2+ exercise days
3. **Live Leaderboard**: Standings page showing points, average days/week, and weekly compliance

## Scope Definition

### In Scope (MVP)

- Checkbox-based weekly submission form (pick name, select week, check days exercised)
- Compliance scoring: 1 point per week with 2+ days of 30+ minute exercise
- Tiebreaker: average exercise days per week
- Leaderboard with cumulative standings across all 20 weeks
- Per-week results view showing each participant's checked days
- Mobile-friendly responsive design
- Dockerized deployment on Vultr VPS behind Cloudflare Zero Trust tunnel
- HTTPS via Cloudflare/Zero Trust SSL

### Out of Scope

- Login system (Cloudflare Zero Trust handles access control)
- Admin page (data corrections done directly on backend/DB)
- Native mobile app
- Social features (comments, reactions, trash talk)
- Exercise verification (GPS, photos, wearable sync)
- Notifications or reminders
- Historical competitions beyond the current 20-week run

## Constraints

### Technical

- **Platform**: Web application (server-rendered HTML)
- **Language**: Python 3.12
- **Hosting**: Small Vultr VPS instance (limited CPU/RAM) -- must be lightweight
- **Auth**: Cloudflare Zero Trust tunnel -- if you can reach the page, you're authorized
- **HTTPS**: Provided by Cloudflare/Zero Trust SSL (no self-managed certs)
- **Database**: SQLite (embeddable, low-resource)

### Business

- **Timeline**: Competition starts week of 2026-03-23 (Monday); app should be usable by Week 1
- **Resources**: Solo developer (Byron), minimal ongoing maintenance
- **Budget**: Existing Vultr instance + existing Cloudflare account

## Assumptions (Resolved)

- [x] **Participants**: Byron Williams, Justin Williams, Nick Williams, Bruce Williams
- [x] **Scoring**: 1 point/week for 2+ exercise days; tiebreaker by average days/week
- [x] **Submissions**: Append-only; admin fixes via backend DB access
- [x] **No admin page**: Direct DB access for data corrections
- [x] **HTTPS**: Via Cloudflare Zero Trust SSL
- [x] **Auth**: Cloudflare Zero Trust tunnel (no app-level auth)

## Related Documents

- [Architecture Decisions](./adr/)
- [Technical Spec](./tech-spec.md)
- [Roadmap](./roadmap.md)
