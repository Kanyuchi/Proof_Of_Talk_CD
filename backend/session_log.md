# Session Log — backend

## 2026-03-19 12:01 — Project initialised
- Documentation files created by Claude Code hook

## 2026-03-19 — Include complimentary tickets from Extasy
- Renamed `PAID_STATUSES` → `VALID_STATUSES = {"PAID", "REDEEMED"}` across 3 files: `extasy_sync.py`, `pipeline_live.py`, `ingest_extasy.py`
- Renamed all `paid_orders` → `valid_orders` variables and updated docstrings/print statements
- Added `paid_amount` and `voucher_code` to enriched_profile in `extasy_sync.py` (was only in Supabase script before)
- Changed `paid_count` → `valid_count` in sync stats dict
- Fixed trailing-slash 307 redirect bug in `pipeline_live.py` API client URLs
- Ran live pipeline: Pierre Kaklamanos (REDEEMED comp ticket) loaded into RDS — 38 total attendees
- Supabase sync blocked: `attendees` table doesn't exist yet in Supabase (migration pending)

## 2026-03-19 — Deploy + enrich + match Pierre Kaklamanos
- Deployed updated code to green EC2 (3.239.218.239) via `push.sh` — health check passed
- Enriched Pierre Kaklamanos: AI summary + intent tags generated (`seeking_partnerships`, `knowledge_exchange`)
- Generated 8 matches for Pierre (top: Steve Wallace @ Monolythic, score 0.74 complementary)
- OpenAI API key confirmed working on EC2 (no 429 errors)
- Supabase `attendees` table still needs manual creation — SQL ready at `scripts/supabase_setup.sql`

## 2026-03-19 — Supabase tables created + attendees synced
- Ran `supabase_setup.sql` via direct Postgres connection — created `attendees`, `matches`, `users` tables + indexes + triggers
- Added `SUPABASE_DB_URL` to `backend/.env` for future automation
- Ran `ingest_extasy.py`: 24/24 attendees inserted into Supabase (0 skipped, 0 errors)
- Verified: 24 attendees in Supabase matches 24 unique valid orders from Extasy API

## 2026-03-19 — Full RDS → Supabase sync
- Synced all 38 attendees, 129 matches, AI summaries, embeddings, and enrichment data from RDS to Supabase
- Supabase is now an exact mirror of RDS (the final production deployment target)
- Cleared previous 24 Extasy-only records and replaced with full dataset including seed + internal profiles

## 2026-03-19 — Add vertical_tags (1000minds sector verticals)
- Added `vertical_tags` column to Attendee model, RDS (Alembic migration), and Supabase
- Created `classify_verticals()` in embeddings.py — GPT-4o classifies attendees into 11 1000minds verticals
- Wired into enrichment routes (batch + single), sync pipeline, and API response schema
- Deployed to green EC2, ran enrichment on all 38 attendees — 38/38 tagged
- Synced vertical_tags to Supabase
- Distribution: investment_and_capital_markets (27), infrastructure_and_scaling (25), tokenisation_of_finance (13), ecosystem_and_foundations (12), decentralized_finance (12), ai_depin_frontier_tech (10), decentralized_ai (7), policy_regulation_macro (5), culture_media_gaming (1)
- 9/11 verticals represented; bitcoin and prediction_markets not yet assigned (no matching attendees)
