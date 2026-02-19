# POT Matchmaker

> **AI-powered matchmaking engine for exclusive, high-stakes events.**
> Built for [Proof of Talk 2026](http://potconf.com) — 2,500 decision-makers at the Louvre Palace, Paris (June 2–3, 2026).

**Live prototype:** http://54.89.55.202
**Author:** Fadzie Kanyuchi
**License:** [CC BY 4.0](./LICENSE) — Attribution required for forks and derivatives

---

## What This Is

POT Matchmaker replaces the randomness of conference networking with a 3-stage AI pipeline that finds non-obvious, high-value connections between attendees — the kind of introductions that would never happen organically.

This is a **Level 3 XVentures Labs Internal Entrepreneur submission**: a working, deployed web application, not a concept document.

---

## Live Demo

| Asset | Link |
|-------|------|
| Live prototype | http://54.89.55.202 |
| API docs (Swagger) | http://54.89.55.202/docs |
| GitHub | https://github.com/Kanyuchi/Proof_Of_Talk_CD |

**Sample AI match output:**

> **Amara Okafor** (Abu Dhabi SWF, $200M mandate) ↔ **Marcus Chen** (VaultBridge CEO, Series B custody infra)
> Score: 0.85 | Type: Complementary
> *"Amara seeks regulated custody solutions; Marcus seeks Middle Eastern sovereign fund investors. VaultBridge has live integrations with 3 European banks. Action: Discuss strategic investment + sovereign fund partnership."*

> **James Whitfield** (NexaLayer CTO, enterprise L2) ↔ **Sophie Bergmann** (Deutsche Bundesbank, CBDC/MiCA)
> Score: 0.65 | Type: Non-Obvious
> *"Sophie's MiCA regulatory sandbox needs compliant infrastructure providers. James's compliance-first L2 is exactly what regulators need to test. This connection would never happen organically."*

---

## Architecture

```
backend/                  Python FastAPI backend
├── app/
│   ├── main.py           FastAPI app entry point
│   ├── core/             Config, database, security
│   ├── models/           SQLAlchemy ORM (Attendee, Match, User)
│   ├── schemas/          Pydantic request/response schemas
│   ├── services/
│   │   ├── matching.py   AI matching pipeline (embeddings + GPT-4o)
│   │   ├── enrichment.py Data enrichment (LinkedIn, Twitter, scraping)
│   │   └── embeddings.py OpenAI embedding generation + vector ops
│   └── api/routes/       REST endpoints (attendees, matches, dashboard)
├── data/                 Seed profiles (5 fictional attendees)
├── tests/                Pytest test suite (55+ tests)
└── alembic/              Database migrations

frontend/                 React + TypeScript (Vite)
├── src/
│   ├── components/       Reusable UI components
│   ├── pages/            Route-level pages
│   ├── api/              Axios API client
│   ├── hooks/            Custom React hooks (React Query)
│   └── types/            TypeScript interfaces
```

### Infrastructure

- **Compute:** AWS EC2 (t3.small, Amazon Linux 2023)
- **Database:** AWS RDS PostgreSQL + pgvector extension
- **Process manager:** Gunicorn (3 workers) + systemd auto-restart
- **Reverse proxy:** nginx (serves React SPA + proxies `/api/*` to FastAPI)
- **Deployment:** `deploy/push.sh` — rsync + SSH automated deploy script

---

## Matching Pipeline

The engine runs 3 stages per attendee:

```
1. EMBED     Each attendee's composite profile (registration + enriched data + AI summary)
             → OpenAI text-embedding-3-small (1,536 dimensions)
             → Stored in pgvector on AWS RDS

2. RETRIEVE  For each attendee, retrieve top-N candidates
             → pgvector cosine similarity (<=> operator)
             → Avoids expensive LLM calls for all N² pairs

3. RANK &    GPT-4o re-ranks candidates considering:
   EXPLAIN   → Complementarity (not just similarity)
             → Deal-readiness (both parties able to transact)
             → Non-obvious connections (different sectors, same underlying need)
             → Generates a natural-language explanation for every match
```

**Match types produced:**
- **Complementary** — investor meets startup in their thesis; regulator meets builders
- **Non-Obvious** — different sectors solving the same underlying problem
- **Deal-Ready** — both parties positioned to transact, not just network

---

## Data Enrichment

Enrichment runs as background jobs per attendee. Sources are layered:

| Source | Data captured |
|--------|--------------|
| Registration form | Name, title, company, goals, interests |
| LinkedIn (Proxycurl API) | Career history, skills, trajectory |
| Twitter/X API | Real-time interests, positioning |
| Company website scraping | What the company actually does |
| Crunchbase | Funding stage, investors, deal activity |

The AI summary is regenerated after each enrichment update.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Query, React Router v7 |
| Database | PostgreSQL on AWS RDS, pgvector extension |
| AI | OpenAI `text-embedding-3-small` (embeddings), `gpt-4o` (match reasoning) |
| Auth | JWT (stateless), bcrypt password hashing, rate limiting |
| Enrichment | Proxycurl (LinkedIn), Twitter API, httpx + BeautifulSoup |
| Infrastructure | AWS EC2 + RDS, nginx, Gunicorn, systemd |

---

## Running Locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL with pgvector extension
- OpenAI API key

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in: DATABASE_URL, OPENAI_API_KEY, SECRET_KEY

# Apply migrations
alembic upgrade head

# Seed test profiles
python scripts/seed_profiles.py

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # dev server on :5173
```

### Run Tests

```bash
cd backend
pytest                                     # all tests
pytest tests/test_matching.py -v          # matching pipeline only
pytest -k "test_complementary" -v         # single test
```

---

## API Reference

The full Swagger UI is available at `/docs` when the server is running.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login` | Login, returns JWT token |
| `GET` | `/api/v1/attendees/` | List all attendees |
| `GET` | `/api/v1/attendees/{id}` | Get attendee profile |
| `POST` | `/api/v1/matches/generate-all` | Run AI matching for all attendees |
| `GET` | `/api/v1/matches/{attendee_id}` | Get matches for an attendee |
| `POST` | `/api/v1/enrichment/batch` | Batch-enrich all attendees *(admin)* |
| `GET` | `/api/v1/dashboard/stats` | Organiser analytics *(admin)* |

---

## Test Profiles

Five fictional attendees representing real archetypes at Web3/finance conferences:

| Name | Role | Profile |
|------|------|---------|
| Amara Okafor | Abu Dhabi SWF | $200M mandate for tokenised real-world assets |
| Marcus Chen | VaultBridge CEO | Series B custody and settlement infrastructure |
| Dr. Elena Vasquez | Meridian Crypto Ventures GP | $500M AUM, TradFi-DeFi thesis |
| James Whitfield | NexaLayer CTO | Enterprise L2 with compliance modules |
| Sophie Bergmann | Deutsche Bundesbank | CBDC research and MiCA regulation |

The engine produces non-obvious connections — e.g. James + Sophie on compliance infrastructure, Amara + Marcus on custody for sovereign funds.

---

## Business Model

| Tier | Price | Description |
|------|-------|-------------|
| White-Label SaaS | €15K–€50K / event | Full-stack deployment under organiser branding |
| Smart Match Upgrade | €500 / attendee | Premium add-on on top of base ticket price |
| Dealflow Intelligence | €50K+ / year | Anonymized signal sold to VC firms and LPs |

**Unit economics (per 2,500-attendee event):**
- COGS: ~€1,650 (AI + infrastructure)
- Revenue (white-label): €25,000
- Gross margin: **~93%**

---

## Deployment

```bash
# Deploy to EC2
./deploy/push.sh <ec2-ip> <path-to-ssh-key>
```

The script:
1. Builds the React frontend
2. rsyncs backend + frontend dist to EC2
3. Restarts the systemd service

---

## Author

**Fadzie Kanyuchi**
- GitHub: [@Kanyuchi](https://github.com/Kanyuchi)
- Project: XVentures Labs Internal Entrepreneur Case Study — Level 3

---

## License

This project is licensed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

You are free to share and adapt this work **provided you give appropriate credit** to the original author (Fadzie Kanyuchi), include a link to the license, and indicate if changes were made.

**You may not use this work without attribution.** See [LICENSE](./LICENSE) for full terms.
