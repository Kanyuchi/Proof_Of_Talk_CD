# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**POT Matchmaker** — AI-powered matchmaking engine for Proof of Talk 2026, a Web3 conference of 2,500 decision-makers at the Louvre Palace, Paris (June 2–3, 2026). The product matches attendees based on complementary needs, non-obvious connections, and deal-readiness — not keyword filtering.

This is a Level 3 submission for the XVentures Labs Internal Entrepreneur case study. It includes a working web app with: data enrichment pipeline, AI matching engine, attendee-facing recommendations, and an organiser dashboard.

## Architecture

```
backend/               Python FastAPI backend
├── app/
│   ├── main.py        FastAPI app entry point
│   ├── core/          Config, database, shared utilities
│   │   ├── config.py  Pydantic settings (env-driven)
│   │   └── database.py SQLAlchemy async engine + session
│   ├── models/        SQLAlchemy ORM models (Attendee, Match)
│   ├── schemas/       Pydantic request/response schemas
│   ├── services/      Business logic layer
│   │   ├── matching.py            3-stage AI matching pipeline (embed → retrieve → GPT-4o rerank)
│   │   ├── embeddings.py          OpenAI embedding generation + vector ops
│   │   ├── enrichment.py          Per-attendee enrichment orchestrator (Voyager LinkedIn fallback, website, etc.)
│   │   ├── enrichment_sweep.py    Daily enrichment cron (03:00 UTC)
│   │   ├── extasy_sync.py         Live Rhuna/Extasy ticket-holder sync
│   │   ├── speakers_sheet_sync.py Master speaker sheet → attendees upsert
│   │   ├── grid_enrichment.py     The Grid B2B GraphQL enrichment
│   │   ├── grid_audit.py          Periodic Grid coverage audit
│   │   ├── slots.py               27-slot June 2/3 schedule grid + mutual-free helper
│   │   ├── concierge.py           AI Concierge chat + proactive field-drafting offers
│   │   ├── sponsor_intelligence.py Live sponsor CRM + per-sponsor report jobs
│   │   ├── engagement.py          Mutual-match alerts + return-visit deltas
│   │   ├── jobs.py                Background-job runner (used for long admin ops)
│   │   ├── email.py               Resend transactional email (all disabled today)
│   │   └── staff_filter.py        Excludes PoT/XVentures staff from candidates
│   ├── api/routes/    REST endpoints
│   │   ├── attendees.py    Profile CRUD + onboarding
│   │   ├── auth.py         Register/login/forgot/reset/me/profile + magic link
│   │   ├── matches.py      Match generation, recommendations, scheduling, magic-link views
│   │   ├── chat.py         AI Concierge + proactive profile-field offer endpoints
│   │   ├── messages.py     Threaded chat on mutual matches
│   │   ├── threads.py      Pre-event vertical discussion threads
│   │   ├── enrichment.py   Trigger data enrichment jobs
│   │   ├── integration.py  Runa integration (magic-link lookup, ticket webhooks)
│   │   └── dashboard.py    Organiser analytics, sponsor reports, sync triggers
│   └── utils/         Helpers (rate limiting, text processing)
├── data/              Reference CSVs (e.g. pot_speakers_master.csv). Seed profiles are gone — see Test Profiles below.
├── tests/             Pytest test suite
├── scripts/           Operational scripts (linkedin_scrape.py, enrich_and_embed.py, exports, audits)
└── alembic/           Database migrations

frontend/              React + TypeScript (Vite)
├── src/
│   ├── components/    Reusable UI components
│   ├── pages/         Route-level pages
│   ├── api/           Axios API client
│   ├── hooks/         Custom React hooks
│   └── types/         TypeScript interfaces
└── public/

docs/                  Product concept, business case, architecture diagrams
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, React Query, React Router v7
- **Database**: Supabase PostgreSQL with pgvector extension for embedding similarity search (migrated from AWS RDS 2026-04-02)
- **AI**: OpenAI API — `text-embedding-3-small` for embeddings (1536 dim), `gpt-4o` for match reasoning/explanations
- **Data Enrichment**: Playwright LinkedIn scraper (primary, operator-driven; replaced dead Proxycurl + dead `linkedin-api`), The Grid GraphQL, httpx + BeautifulSoup for company-site scraping
- **Infrastructure**: Railway (backend), Netlify (frontend), Supabase (database — shared with 1000 Minds app), Resend (email — all sends currently disabled)

## Commands

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest
pytest tests/test_matching.py -v          # single test file
pytest -k "test_complementary" -v         # single test by name

# Database migrations
alembic upgrade head                      # apply all migrations
alembic revision --autogenerate -m "msg"  # create new migration

# LinkedIn enrichment (operator-driven, manual browser login)
python scripts/linkedin_scrape.py                      # process pending queue
python scripts/linkedin_scrape.py --missing-photos-only --limit 30  # photo backfill batch

# Batch enrichment + embedding refresh
python scripts/enrich_and_embed.py --skip-linkedin     # everything except LinkedIn
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # dev server on :5173
npm run build        # production build
npm run preview      # preview production build
```

## Key Design Decisions

### Matching Pipeline (3-stage)
1. **Embed**: Each attendee's composite profile (registration + enriched data + AI summary) is embedded via OpenAI `text-embedding-3-small` and stored in pgvector.
2. **Retrieve**: For each attendee, retrieve top-N candidates by cosine similarity using pgvector's `<=>` operator.
3. **Rank & Explain**: GPT-4o re-ranks candidates considering complementarity (not just similarity), deal-readiness, and non-obvious connections. It generates natural-language explanations for each match.

This 3-stage approach avoids expensive LLM calls for all N^2 pairs while still producing nuanced, explainable matches.

### Match Types
- **Complementary**: Investor meets startup in their thesis; regulator meets builders
- **Non-obvious**: Different sectors solving the same underlying problem
- **Deal-ready**: Both parties in a position to transact, not just network

### Data Enrichment Strategy
Enrichment runs as background jobs per attendee. Sources are layered:
- Registration form data (always available, shallow)
- The Grid B2B (verified Web3 company data — sector, products, description). Name search with URL/email-domain fallback.
- Company website scraping (meta descriptions, page text)
- **LinkedIn — Playwright script is the primary tool** (`scripts/linkedin_scrape.py`). Manual browser login (handles 2FA), then iterates through the pending queue with 10s delays. The previously-used `linkedin-api` library was killed by LinkedIn 403s on 2026-04-29; Voyager cookies remain a fallback. LinkedIn enrichment is **decoupled from the daily cron** — operator runs the script ad-hoc when the dashboard's pending count climbs (weekly Monday 09:00 BST reminder via routine `trig_014y5YF5MyAHgVG4CQ2e2c9a`).
- Twitter/X handle stored, no scraping today.

**Daily cron jobs (UTC):**
- 02:00 — Extasy ticket-holder sync
- 02:15 — Speaker sheet sync
- 02:30 — Grid audit
- 02:45 — Match refresh
- 03:00 — Enrichment sweep (Grid + website + AI summary + embedding for new rows)

Each cron writes a row to `sync_status` (heartbeat table) so silent failures are visible on the dashboard.

AI summaries have anti-hallucination guardrails: sparse profiles (no interests, no goals, no meaningful enrichment) get factual stubs instead of GPT-generated fabrications. `profile_data_quality()` in `concierge.py` is the single source of truth for SPARSE/PARTIAL/GOOD, used by both `_brief_attendee_line` and `draft_field_candidates`.

### AI Concierge
Authenticated chat (`/chat/concierge`) with persisted history (`chat_messages` table, 12-turn prompt window). When an attendee opens chat with < 80% profile completeness, `ProfilePromptOffer` surfaces a tailored welcome: GPT-4o drafts 2-3 candidates for the next missing high-impact field (goals → target_companies → interests → photo_url). Save triggers a background re-embed + match refresh (skipped for `photo_url`, which doesn't affect matching). Maybe-later persists a 30-day decline cooldown via `enriched_profile.field_prompts.{field}.state`. See `docs/superpowers/specs/2026-05-13-concierge-field-drafting-design.md`.

### Match-card Features (Phase 2 — return-visit hooks)
- **Free-slot visibility**: `MatchResponse.mutual_free_slots` populated for mutual matches with no booking; UI shows up to 4 "Both free at — tap to book" chips. `PATCH /schedule` returns 409 on double-booking. See `services/slots.py`.
- **Magic-link access**: `/m/:token` route + `magic_access_token` column. Attendees can review matches and self-fill profile fields without logging in.
- **Privacy mode**: Anonymous/pseudonymous B2B-only profiles, name + photo + socials revealed only on mutual match.

### Sponsor Data
Sponsor intelligence reports pull live data from the CEO Dashboard's Supabase project (`emsofswnzqnepekmiwwp`) via REST API. The `SPONSORS` list in `sponsor_intelligence.py` is a fallback — live data comes from `dashboard_snapshots.data.sponsorsCRM` (37 sponsors from the Google Sheet CRM). Requires `CEO_DASH_SUPABASE_URL` and `CEO_DASH_SUPABASE_ANON_KEY` env vars.

### Ferd's Outreach Sheet Sync
Google Apps Script bound to `PoT26_Master_Email_Database_v3` syncs Supabase attendees + nominations into a `POT Attendees` tab daily at 11 PM. ARRAYFORMULA-based `In Funnel` column on all feeder tabs (COLD, Close network) flags contacts already in the funnel. Repo copy of script at `docs/integrations/sheets_sync/Code.gs`.

### Attendee Profile Embedding
The embedding is generated from a composite text blob combining: name, title, company, goals, interests, AI summary, and enriched data highlights. This ensures the vector captures the full picture, not just registration keywords.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:
- `DATABASE_URL` — Supabase PostgreSQL connection string; format: `postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres`
- `OPENAI_API_KEY` — required for embeddings and match explanations
- `RESEND_API_KEY` — Resend email delivery (production, no sandbox)
- `RESEND_FROM_EMAIL` — sender address (`matches@proofoftalk.io`)
- `SECRET_KEY` — JWT signing key
- `APP_PUBLIC_URL` — public URL (`https://meet.proofoftalk.io`)
- `INTEGRATION_API_KEY` — Runa integration auth
- `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD` — credentials used by the Playwright scraper login (`scripts/linkedin_scrape.py`). The old `linkedin-api` Python library path was removed 2026-05-01 after LinkedIn started 403'ing it.
- `LINKEDIN_LI_AT_COOKIE`, `LINKEDIN_CSRF_TOKEN` — legacy Voyager cookies; fallback only, rarely needed
- `PROXYCURL_API_KEY` — **defunct** (Proxycurl sunset, API returns 410)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — Supabase REST API (for data ingestion scripts)
- `CEO_DASH_SUPABASE_URL`, `CEO_DASH_SUPABASE_ANON_KEY` — CEO Dashboard Supabase (for live sponsor data)

## Test Profiles & Production Data

The 5 original case-study seeds (Amara Okafor, Marcus Chen, etc.) have been **deleted** from production Supabase (2026-04-14). The database now contains only real attendees from Rhuna/Extasy + the master speaker sheet (~363 rows as of 2026-05-13). Do not re-seed.

The matching engine should produce non-obvious complementary connections from real attendees — investor ↔ founder in thesis, regulator ↔ builder, custody/compliance crossovers, etc. ICP signals (`offers`, `ideal_customers`, `ideal_partners`, `anti_personas`) are GPT-4o-inferred per attendee and feed into both the embedding and the rerank prompt.
