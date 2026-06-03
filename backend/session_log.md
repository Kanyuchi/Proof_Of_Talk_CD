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

## 2026-05-21 — [sync] Fixed all Sync Health errors + partials (commit 8293c9b)
- Investigated via 2 parallel subagents reading sync_status.stats + code + live DB. Root causes:
  - **daily_grid_audit ERROR**: terminal `grid_audit_runs` INSERT ran after the 448s Grid loop on a dropped direct-:5432 connection (pre_ping only validates at checkout). **daily_match_refresh ERROR**: its target-fetch retry was broken — reassigned the session but never re-ran the SELECT → silently returned 0 targets / surfaced the drop.
  - **extasy PARTIAL (58 errors/1 chunk)**: ONE transient connection drop mis-counted ~2x — per-row `except` swallowed connection errors (every remaining row on the dead session = an "error") + the failed commit re-counted the chunk while crediting un-committed inserts. Data itself clean (0 null/dup emails).
  - **speakers PARTIAL (1 error)**: sheet row "Nenter (Nathan) Chow" listed twice with different companies (Naoris Protocol vs BitMart); the email-less row's placeholder email collided (23505) with the existing row nightly.
- Fixes: new `core/database.py::run_with_db_retry()` (fresh session + retry-once on connection-drop) wrapping grid_audit's terminal INSERT + initial SELECT and match_refresh's target fetch; extasy now re-raises connection errors, retries the chunk on a fresh session, credits inserted/backfilled only post-commit, and persists `stats.error_reasons`; `ingest_speakers_sheet.py` find_existing adds a placeholder-email lookup + treats 23505 as noop-with-warning. Tests +2 files, suite **104 passed**.
- Verification: unit tests simulate the drop+retry; agents reproduced extasy (0 errors on healthy sessions) and the speaker resolution (RESOLVED→noop) against live data.
- **SMOKE-TESTED ON PROD (2026-05-21 ~18:00–18:13Z)**: ran all 4 jobs via their real cron entrypoints against prod; all flipped sync_status to **ok**. daily_match_refresh ok (32 matches, failed=0); daily_speakers_sync ok (errors 1→**0**); daily_extasy_sync ok (errors 58→**0**, chunks_failed→0, error_reasons={}); daily_grid_audit ok (terminal INSERT persisted, 253 matched). Fixes confirmed live, not just unit-tested. (Legacy alias rows extasy_sync/speakers_sheet_sync refresh on the next nightly run.)
- RECOMMEND to ops (not code): dedupe Nathan Chow in the speaker sheet (pick Naoris vs BitMart); investigate `sithum@proofoftalk.io` having 2 attendee rows despite the unique constraint (likely email case-sensitivity).

## 2026-05-21 — [data] Deleted duplicate sithum@proofoftalk.io attendee row
- Two rows existed (case-sensitive unique index let a cron insert a lowercase dup next to the original): `70c58bf1` "Sithum@…" (created 05-13, has the login user + 8 matches) vs `9e842cde` "sithum@…" (cron-created 05-14, NO user, 6 matches).
- Deleted the dup `9e842cde` + its 6 matches atomically (verified: 0 users linked first, FK rules are NO ACTION so matches deleted in the same statement). Only the real login row remains (users_linked=1, 8 matches). First attempt hit a connection timeout (no-op, verified before retry); retry succeeded (matches_deleted=6, attendees_deleted=1).
- ROOT CAUSE to fix later: `attendees.email` unique index is case-sensitive → recurs whenever an email's case differs between sources. Recommend a case-insensitive unique constraint (lower(email)) + dedupe-by-lower(email) in the syncs.

## 2026-05-21 — [session wrap] LinkedIn enrichment recency check (read-only)
- Q: when did LinkedIn enrichment last run? Authoritative stamp = `enriched_profile.linkedin_enriched_at` (set by both `scripts/linkedin_scrape.py` AND the enrichment orchestrator's LinkedIn fallback).
- State: 421 attendees ever LinkedIn-enriched; 242 in last 7d; 37 in last 24h; most recent stamp 2026-05-21T18:06 — but that coincides with today's extasy-sync enrichment of new rows (the auto-fallback path), NOT a manual operator Playwright scrape.
- Last evidence of a MANUAL operator scrape session: exports `attendees_missing_linkedin_20260504.xlsx` (May 4) + `diagnose_photo_dom.json` photo diagnostic (May 19). `updated_at` is useless as a proxy (sweep/match-refresh touch every row).
- Session covered: Tommi/forgot-password fix + surgical force (deployed), pending-count 422 fix (deployed+verified), bulk-rebuild blast guard (notify=False), all 4 sync crons fixed + SMOKE-TESTED green on prod, welcome waves 2+3 (261 sent/462 remaining), deleted duplicate sithum attendee row.

## 2026-06-02 12:45 — [meeting-times-tz] Systemic fix (app = source of truth), not per-person; B2B Lounge backfill

- Clarified intent: do NOT rewrite anyone's meeting time. The app time is the single source of truth; the confusion was app (13:00) vs the old email (11:00). Fix is systemic for everyone, not an Olga-specific email — dropped scripts/send_olga_glen_confirmation.py.
- Frontend (concurrent-session edit, kept): formatMeetingTime/formatSlotChip now render in Europe/Paris via toInstant(), labeled "(Louvre time)" — app + email now agree for every viewer on any device.
- Backfilled meeting_location for all 243 booked matches: 'Louvre Palace, Paris (exact spot shared...)' -> 'B2B Lounge, Louvre Palace' so the B2B Lounge point shows for everyone already booked, not just new bookings.
- No meeting_time values changed.

## 2026-06-02 18:35 — [account-recovery] Created missing attendee row for Jesus Lander (jedlanca@gmail.com)
- Problem: Jesus Lander couldn't activate/register. He bought nothing himself - his General Pass was assigned to him on order JGUGc2sTHz, **bought by Jean-Andre Villamizar** (jean@HODLmarkets.com). extasy_sync is buyer-keyed, so it only created the buyer's attendee row; Jesus had no row. Registration's live-Extasy fallback (find_extasy_order_by_email) searches the ORDERS feed by email, and jedlanca@gmail.com only appears in the TICKETS feed -> he'd hit "we couldn't find a ticket".
- Fix: created attendee 98ed2763-ef96-4f98-80a0-e8ada6518a60 from his tickets-feed row via attendee_from_extasy_order (General Pass -> DELEGATE, country GBR, phone +447539501349, source=extasy_ticket_recovery, ticket_qr SvXDXb59, buyer_email recorded). Assigned magic_access_token.
- Ran run_full_enrichment + refresh_profile_matches (same as register flow): embedding set, **17 matches** generated. enriched_at still NULL (sparse gmail profile -> factual stub; harmless, re-runs on first register).
- He can now register at meet.proofoftalk.io with jedlanca@gmail.com and pass the ticket gate.
- CLASS OF BUG: anyone whose ticket was bought/assigned by a different buyer is invisible to the buyer-keyed sync + the orders-only register fallback. Recommend: extend find_extasy_order_by_email (or a sweep) to also match the TICKETS feed by ticket-holder email.

## 2026-06-02 19:10 — [match-id-stability] Regen reuses match rows in place (fixes accept/reject not saving)
- SYMPTOM (Jesus Lander, live event): accepts intermittently not saving; rejects never saving (DB showed 10 accepted, 0 declined despite him rejecting) -> rejected matches kept reappearing.
- ROOT CAUSE: generate_matches_for_attendee regen was delete+recreate. `_purge_stale_matches_and_collect_locked` DELETED stale pending rows up front, then `_persist_ranked` re-INSERTED them with a NEW uuid every regen. Any client holding the old match id 404'd on PATCH /matches/{id}/status -> action silently lost; the un-declined pair regenerated as fresh pending -> "reject reappears". Churn was constant because ANY pending counterpart editing their profile triggers a regen that deletes the shared pending row.
- FIX (non-destructive regen, stable ids):
  - `_purge_stale_matches_and_collect_locked` -> replaced by `_collect_locked_counterparts` (returns user-touched counterparts to exclude from candidate gen; NEVER deletes).
  - `_persist_ranked`: when a stale pending row exists for the pair, REFRESH it in place (same id, preserve status); only insert when truly new. Added `_is_stale_pending` guard so user-touched rows are never overwritten.
  - `_prune_unreferenced_pending`: removes only fully-stale pending rows whose counterpart genuinely dropped out of the retrieval pool; `keep_ids` spares re-persisted survivors and `keep_counterparts` spares pool members that dipped below the GPT floor this run.
  - `_apply_priority_intros` force-add now reuses a pre-existing row for the pair (no IntegrityError, not pruned).
- VERIFIED: full suite 457 passed (rewrote test_matching_preservation.py to the new contract + id-stability/preservation unit tests). Prod smoke test on Jesus: 3 consecutive regens -> 17/17 existing pair ids STABLE, 10/10 accepts preserved (was 0/17 stable under old code).
- Preserves the David Chapman (2026-05-26) contract: accepts/declines/scheduled/hidden never wiped.

## 2026-06-02 19:35 — [account-merge] Merged duplicate Razvan Paun records + made extasy_sync merge-stable
- Two attendee rows for one person: b718e15c (razvan@dragonflydigitalassets.fund, Dragonfly Asset Management, rich profile + login account registered today, 10 matches) and 5d2e3d4f (razvanmarianp@gmail.com, blank company, no login, but held his actual Extasy General Pass order e8c8f68b + phone/city, 21 matches).
- MERGE (single tx): survivor = b718e15c (login + rich profile). Backfilled phone (+447933180090), city (Valencia), extasy_order_id/ticket_name/ticket_bought_at from the dupe. Repointed the dupe's 21 matches onto survivor (verified shared counterparties=0, so no uq_matches_pair collision; not matched to each other, so no self-match). Deleted the dupe. Survivor now has 31 distinct matches, 1 login, 0 orphan matches. No messages/threads/intros referenced either row.
- RESURRECTION FIX (extasy_sync.py): sync upserted by email only -> tonight's 02:00 run would not find the survivor under the gmail buyer email and would re-INSERT the dupe (which the 03:30 net-new cron would then regenerate a parallel match set for). Changed the lookup to match an attendee already carrying this extasy_order_id FIRST, then fall back to email. Survivor carries order e8c8f68b, so the sync now recognizes and skips it. Login unaffected (keyed on users.email, not attendees.email).
- VERIFIED: module imports clean; live-DB check confirms order e8c8f68b resolves to b718e15c with 0 stray gmail rows.
- CLASS OF BUG: any account merge where the survivor keeps a different login email than the Rhuna buyer email was previously undone on the next sync. order_id-first matching fixes it generally, not just for Razvan.

## 2026-06-02 19:55 — [match-volume] Bumped Cotabe Moral to 50+ matches (live event)
- Cotabe Moral (90f17fdf, Giveth / Head of Partnerships, DELEGATE) had only 19 matches (17 pending + 2 accepted). Wanted more people to meet on the floor.
- Ran generate_matches_for_attendee(top_k=50, clear_existing=True, notify=False): pool = max(50, DEEP_POOL_SIZE=20) -> 50 retrieved, 8 GPT-curated + deep tail. Persisted 43 this run.
- RESULT: 53 distinct people (51 pending + 2 accepted). Both accepts preserved (non-destructive regen, locked counterparts reused in place). No emails.
- No code change - operational data action only.

## 2026-06-02 20:05 — [match-mutual-label] Fix false "Mutual match — both accepted!" on one-sided accept
- BUG (Cotabe, live event): clicking "I'd like to meet" while the OTHER party is still pending flipped the card to "Mutual match — both accepted!", implying the other had accepted.
- ROOT CAUSE: frontend optimistic update in `frontend/src/hooks/useMatches.ts` (useUpdateMatchStatus.onMutate) stamped the clicked value straight onto the AGGREGATE `status` (`{...m, status}`). The cards derive `isMutual = match.status === "accepted"`, so a one-sided accept set status="accepted" locally -> instant false mutual. Backend was correct (overall recomputed to "pending"); the lie was purely the optimistic local write, visible until refetch.
- FIX: onMutate now sets only the VIEWER's per-side field (status_a/status_b, side via attendee_a_id===attendeeId, same pattern as myStatusFor) and recomputes the aggregate with `computeOverallStatus`, a faithful mirror of backend `_compute_overall_status`. Added a `prev` snapshot + onError rollback. Covers both AttendeeMatches and MyMatches (shared hook).
- VERIFIED: prod build clean (typecheck passes); standalone logic test: one-sided accept -> status "pending" (isMutual false), genuine both-accepted -> "accepted" (isMutual true), decline -> "declined". Did NOT browser-test against a real attendee (would mutate live match state mid-event); demo personas have no real pending matches to exercise the path.

## 2026-06-03 10:05 — [match-visibility-override] Opened 50+ more matches to Jesus Lander (only him)
- Request: surface +50 more matches for Jesus on top of his existing set, visible to him only, and run enrichment on both sides.
- Two layers fixed: (a) match POOL (DELEGATE default 20 candidates) and (b) per-viewer VISIBILITY cap (match_visibility.TIER_LIMITS max 20 at GOOD).
- CODE: added `_viewer_limit(attendee, tier)` in api/routes/matches.py - reads optional `enriched_profile.match_visibility_limit` override, else falls back to tier_limit. Applied to both authed get_matches and magic-link get_matches. No migration (JSONB). Scoped to whoever has the key set (only Jesus today). Unit test added.
- DATA (Jesus 98ed2763 only): re-enriched him (run_full_enrichment -> re-embed; LinkedIn private, no website), generated expanded pool top_k=70 via stable-id engine, set enriched_profile.match_visibility_limit=70.
- RESULT: 71 match rows (61 pending + 10 accepted preserved). All 71 candidates already enriched (0 needed it) -> candidate-side enrichment was a no-op. He'll see all 71 once deploy lands.
- VERIFIED LIVE (deploy 4df889a SUCCESS): GET /matches as Jesus's own user -> visible_count=70 (was tier-capped at 20), tier=GOOD. 1 "locked" is a card he deferred himself (hidden while fresh exist, by design). Override left at 100 as headroom. Accepts preserved through the expansion.
