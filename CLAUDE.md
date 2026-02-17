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
- **Database**: PostgreSQL on AWS RDS with pgvector extension for embedding similarity search
- **AI**: OpenAI API — `text-embedding-3-small` for embeddings (1536 dim), `gpt-4o` for match reasoning/explanations
- **Data Enrichment**: Proxycurl (LinkedIn), Twitter API, httpx + BeautifulSoup for web scraping
- **Infrastructure**: AWS (RDS, optionally S3, EC2/ECS for deployment)

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
- LinkedIn via Proxycurl API (career history, skills, trajectory)
- Twitter/X API (real-time interests, positioning)
- Company website scraping (what the company actually does)
- Crunchbase data (funding, investors, deal stage)

The AI summary is regenerated after each enrichment update.

### Attendee Profile Embedding
The embedding is generated from a composite text blob combining: name, title, company, goals, interests, AI summary, and enriched data highlights. This ensures the vector captures the full picture, not just registration keywords.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:
- `DATABASE_URL` — AWS RDS PostgreSQL connection string (must have pgvector extension)
- `OPENAI_API_KEY` — required for embeddings and match explanations
- `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — AWS credentials
- `PROXYCURL_API_KEY` — optional, for LinkedIn enrichment
- `TWITTER_BEARER_TOKEN` — optional, for Twitter enrichment

## Test Profiles

Five fictional attendees from the case study are in `backend/data/seed_profiles.json`. These are the primary demo data:
1. **Amara Okafor** — Abu Dhabi SWF, $200M mandate for tokenised RWA
2. **Marcus Chen** — VaultBridge CEO, Series B custody/settlement infra
3. **Dr. Elena Vasquez** — Meridian Crypto Ventures GP, $500M AUM, TradFi-DeFi thesis
4. **James Whitfield** — NexaLayer CTO, enterprise L2 with compliance modules
5. **Sophie Bergmann** — Deutsche Bundesbank, CBDC and MiCA regulation

The matching engine must produce non-obvious connections between these profiles (e.g., James + Sophie on compliance infrastructure, Amara + Marcus on custody for sovereign funds).
