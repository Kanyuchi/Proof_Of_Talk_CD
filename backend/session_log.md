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
