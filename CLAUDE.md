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
│   │   ├── matching.py     AI matching pipeline (embeddings + GPT-4o scoring)
│   │   ├── enrichment.py   Data enrichment (LinkedIn, Twitter, web scraping)
│   │   └── embeddings.py   OpenAI embedding generation + vector ops
│   ├── api/routes/    REST endpoints
│   │   ├── attendees.py    CRUD for attendee profiles
│   │   ├── matches.py      Match generation + recommendations
│   │   ├── enrichment.py   Trigger data enrichment jobs
│   │   └── dashboard.py    Organiser analytics
│   └── utils/         Helpers (rate limiting, text processing)
├── data/              Seed data (5 test profiles from case study)
├── tests/             Pytest test suite
├── scripts/           One-off scripts (seed DB, run enrichment batch)
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
- **Data Enrichment**: Proxycurl (LinkedIn), Twitter API, httpx + BeautifulSoup for web scraping
- **Infrastructure**: Railway (backend), Netlify (frontend), Supabase (database — shared with 1000 Minds app), Resend (email)

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

# Seed test profiles
python scripts/seed_profiles.py
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
- The Grid B2B (verified Web3 company data — sector, products, description)
- Company website scraping (meta descriptions, page text)
- LinkedIn — **currently non-functional** (Voyager API deprecated, Proxycurl sunset/moved to NinjaPear at $49/mo). Registration form collects LinkedIn URLs but automated enrichment is dead.
- Twitter/X API (real-time interests, positioning)
- Crunchbase data (funding, investors, deal stage)

AI summaries have anti-hallucination guardrails: sparse profiles (no interests, no goals, no meaningful enrichment) get factual stubs instead of GPT-generated fabrications. The `generate_ai_summary()` function in both `embeddings.py` and `enrich_and_embed.py` checks data completeness before calling GPT.

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
- `PROXYCURL_API_KEY` — **defunct** (Proxycurl sunset, API returns 410)
- `LINKEDIN_LI_AT_COOKIE`, `LINKEDIN_CSRF_TOKEN` — LinkedIn Voyager cookies (expire weekly, **Voyager API currently deprecated**)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — Supabase REST API (for data ingestion scripts)
- `CEO_DASH_SUPABASE_URL`, `CEO_DASH_SUPABASE_ANON_KEY` — CEO Dashboard Supabase (for live sponsor data)

## Test Profiles

The 5 original case-study seeds (Amara Okafor, Marcus Chen, etc.) have been **deleted** from production Supabase (2026-04-14). The database now contains only real attendees from Rhuna/Extasy + 1000 Minds speaker sync. Do not re-seed.

The matching engine must produce non-obvious connections between these profiles (e.g., James + Sophie on compliance infrastructure, Amara + Marcus on custody for sovereign funds).
