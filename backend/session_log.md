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

## 2026-05-21 — [launch] Batch welcome-sender + go-live readiness audit
- Built `scripts/send_welcome_batch.py`: staged welcome-email sender for the existing pool. Preview by default; `--confirm` to send; `--limit` waves; `--only` for smoke tests; `--status` for remaining count. Local ledger `exports/welcome_sent.log` prevents double-sends.
- Excludes: opted-out, gated speakers (matching_consent pending/declined), rows with no magic_access_token (broken link), already-sent.
- email.py: added `force` param to `_send_email` + `send_welcome_email` — bypasses EMAIL_MODE gate for a deliberate operator batch, so automated triggers stay gated (EMAIL_MODE=allowlist) while ops blast welcomes. `send_welcome_email` now returns the send result.
- Readiness audit (live DB): 737 attendees, all have email; only 43 have magic_access_token → **678 need backfill** before any welcome (one call: POST /matches/generate-tokens); 717/737 have ≥1 match (content ready); 16 gated; 0 opt-outs.
- Load finding: DATABASE_URL is the **direct** Supabase connection (db.…:5432), not the pooler — connection-exhaustion risk under a true simultaneous spike. Welcome-link clicks hit read-only /m/{token} (precomputed matches), so staged waves are safe; recommend pooler (6543, transaction mode) before any big-bang.
- Verdict: NOT ready for one big-bang. Staged path = backfill tokens → smoke-test → waves of ~50–100/day. EMAIL_MODE still allowlist (not flipped).

## 2026-05-21 — [launch] Cleared the two go-live blockers
- Magic tokens: ran `scripts/backfill_magic_tokens.py` (new, mirrors POST /matches/generate-tokens). Backfilled 694 → **737/737 attendees now have a magic_access_token**; welcome batch eligibility 43 → **721** (16 gated excluded). Welcome links no longer dead-end at the login wall.
- DB connection hardened (`app/core/database.py`): added `pool_pre_ping=True` (Supabase drops idle conns → was a source of intermittent 500s), `pool_recycle=1800`, explicit `pool_size`/`max_overflow` (env-tunable via DB_POOL_SIZE/DB_MAX_OVERFLOW, defaults 5/10), and pooler-awareness — auto-sets `statement_cache_size=0` when DATABASE_URL points at the transaction-mode pooler (:6543), so flipping to the pooler for spike capacity is now a safe one-line env change. Smoke-tested: connects, `select 1` OK.
- Note: 12 pre-existing test failures (embeddings/enrichment/rerank/scalability mocks) confirmed unrelated (identical with these changes stashed).

## 2026-05-21 — [auth] Tommi login fix + forgot-password dead-end closed for the unclaimed pool
- Reported issue: Tommi Vuorenmaa (to@rayleigh.re) "can't access login." Diagnosis: she HAS an attendee row + magic token (consent not_required, not opted out) but **no User row / no password**. She did receive the first welcome wave (ledger 2026-05-21T13:21:11 — the ledger keys on email, so a name-grep misses her). Login (email+password) 401s for her because she never claimed via the magic link.
- Root cause is systemic, not Tommi-specific: 739 attendees, only **40 have a login account → 700 unclaimed**. Login only works after claiming via the welcome email's "Unlock Full Access" CTA (`/m/{token}?unlock=1` → set password). Claim flow itself works (10+ external claims in the hours after the 13:20 batch: nmehta, kapil, y.heinze, aj@veda.tech, hedeyeh.taheri…). Two self-service paths dead-end for the unclaimed: login → 401; **forgot-password → silent no-op** (only emailed if a User row exists).
- Immediate fix: resent Tommi's welcome email via `send_welcome_batch.py --only to@rayleigh.re --confirm` (removed her stale ledger line first so the dedup wouldn't skip her). FROM = warm `team@xventures.de`, sent=1 failed=0.
- Systemic fix (`api/routes/auth.py` forgot_password): when no User exists, fall back to looking up an attendee at that email; if found with a magic token, send the welcome/claim email (CTA → set password) instead of doing nothing. NOT force=True (request-triggered), so it stays gated by EMAIL_MODE like all automated mail — reaches the full pool only once EMAIL_MODE flips to "all"; until then ops resend via the batch. No account-enumeration change (identical generic response).
- Tests: new `tests/test_auth_forgot_password.py` (4 cases: existing user→reset; unclaimed attendee+token→welcome; unknown→nothing; attendee w/o token→nothing). Full suite **95 passed, 0 failed** (no regression).

## 2026-05-21 — [launch] Welcome wave 2 (next 100) sent
- Sent the next welcome wave via `send_welcome_batch.py --limit 100 --confirm`: **sent=100, failed=0**, FROM warm `team@xventures.de`. Ledger now **162 sent / 561 eligible remaining**.
- Mauricio Magaldi Suguihura (`mauricio.magaldi@gmail.com`) confirmed included — landed at position 100 of the wave (sent 18:46:54). Note: a *different* attendee "Mauricio Gonzalez, PhD" (hello@euler-advisory.com) exists; only Magaldi Suguihura was targeted.
- Lesson: the batch preview prints only the first 10 targets + "… and N more", so grepping preview output for a specific later-positioned email gives a false negative — verify inclusion via the ledger after send, not the preview.
- Reminder for the 700-unclaimed self-recovery: EMAIL_MODE is still `allowlist` on Railway. The shipped forgot-password fallback (commit 324e8a9) only reaches attendees once EMAIL_MODE is flipped to `all` (launch-wide decision — un-gates all automated mail). Until then, ops resend welcomes via the batch.

## 2026-05-21 — [auth] Surgical fix DEPLOYED: forgot-password self-recovery works without flipping EMAIL_MODE
- Decision: rather than flip EMAIL_MODE=all (which un-gates ALL automated mail — incl. a latent 739-blast via the "regenerate all matches" path `generate_all_matches` → per-attendee `send_match_intro_email`), made the forgot-password recovery email `force`-send only. Keeps match-intro / mutual-match / meeting-confirmation emails gated on `allowlist`; opens just the on-demand recovery path. EMAIL_MODE unchanged.
- Code (commit 3c303de): `auth.forgot_password` unclaimed-attendee branch now calls `send_welcome_email(..., force=True)`. Documented as a deliberate, scoped exception to "no force from a request path" — safe because user-initiated, rate-limited (3/min), and only ever addressed to the email already on the attendee row. Test asserts `force=True`. 4/4 pass.
- Deploy: Railway auto-deploys on push to main. Pushed 16:56:31Z → deployment c8a80f7c SUCCESS (18:56:32 +02:00). Backend = https://proofoftalkcd-production.up.railway.app, routes under /api/v1 (note: /docs + openapi disabled → 404 is expected; not a health signal).
- Smoke test (prod): POST /api/v1/auth/forgot-password for nonexistent email → 200 generic msg (no send); for Tommi (to@rayleigh.re, still unclaimed) → 200 generic msg (force claim email). Identical responses = enumeration-safe. Could NOT see a per-send log line: `railway logs` surfaces only uvicorn access/startup lines, not app `logger.info` — so absence ≠ no-send. Confidence rests on: deploy live + 200 on the unclaimed branch + unit test + the identical force path having delivered 100 welcome emails 12 min earlier.
- Observed in prod logs (NOT mine — flagging, not fixing): `GET /api/v1/matches/pending-count` returns **422 repeatedly** for a live user — looks like a missing/!required query param (e.g. attendee_id). Pre-existing; worth a separate fix.

## 2026-05-21 — [matches] Fixed /pending-count 422 (route shadowing) — DEPLOYED + VERIFIED
- Root cause (not a missing param): `GET /matches/{attendee_id}` (attendee_id: UUID) was declared BEFORE the static `GET /matches/pending-count`. Starlette matches in declaration order → "pending-count" parsed as attendee_id → `uuid_parsing` 422; the real pending-count handler was unreachable dead code.
- Fix (commit fbfd954): moved `/pending-count` above the `/{attendee_id}` catch-all, with a guard comment ("static routes before parameterized"). Added `tests/test_pending_count_route.py` (TestClient + dep overrides for require_auth/get_db, `raise_server_exceptions=False`) — reproduced 422 first, then green. Full suite **97 passed**.
- Deploy: Railway 149906df SUCCESS (19:15:06 +02:00). Prod verify: `GET /api/v1/matches/pending-count` unauth now **401 "Not authenticated"** (was 422) → route no longer shadowed; authed users get `{"pending_count": N}`.
- General lesson for this router: any future literal GET path must go ABOVE line ~100 `/{attendee_id}`, or it'll be swallowed and 422.

## 2026-05-21 — [matching] Bulk-rebuild blast guard + [launch] welcome wave 3
- Guard (commit 85b41d3): `generate_matches_for_attendee` gains `notify` (default True); `generate_all_matches` now passes `notify=False` so a full match rebuild no longer fires one intro email per attendee (~739-blast). Genuine new-match paths (registration, nightly new-attendee cron) keep notify=True. This removes the last footgun blocking the EMAIL_MODE=all launch flip. Test: `tests/test_generate_all_no_notify.py`; full suite **98 passed**. Railway auto-deploy triggered on push.
- Welcome wave 3: `send_welcome_batch.py --limit 100 --confirm` → **sent=100, failed=0**. Ledger now **261 sent / 462 eligible remaining**.
