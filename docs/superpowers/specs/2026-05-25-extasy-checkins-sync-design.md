# Extasy Check-ins Sync — recover per-attendee claimed-pass data

**Date:** 2026-05-25
**Status:** Approved (design), pending implementation plan
**Author:** Claude + Shaun

## Problem

The matchmaker shows 945 "decision-makers registered" while the CEO ticketing
dashboard shows 1065 confirmed tickets. The reconciliation (see
`memory/reference_matchmaker_vs_ceo_dashboard_count.md`) decomposes the 120 gap
as: −33 status/timing, **−150 dedup (tickets→people)**, +63 non-Rhuna additions.

The −150 exists because the matchmaker's only Rhuna source today is the
**`orders`/`tickets`** feed, which is keyed on the **buyer**. A company that
buys 10 passes under one buyer email collapses to a single attendee row, and a
pass bought without a per-attendee email cannot become a profile at all.

The Extasy **`checkins`** report is **per-attendee**: when an individual claims /
personalizes their pass, a check-in record is created carrying that real
holder's own email, name, company, and job title. Ingesting it recovers the
real people the buyer-keyed feed misses.

## Evidence (measured 2026-05-25)

- Endpoint `https://api.b2b.extasy.com/operations/reports/checkins/{EVENT_ID}`
  is a sibling of the existing `orders`/`tickets` endpoints. **No auth** — the
  event UUID is the only gate, identical to the feeds already in use. No
  service-point email is required.
- Returns CSV (`text/csv; ISO-8859-1`), parseable by the existing `_fetch_csv`.
- 396 check-in rows · 381 distinct emails · **0 blank emails** · 2 test/QA rows.
- Cross-referenced against the 944 matchmaker emails: **337 already present, 44
  net-new recoverable** across 41 companies (Stabolut, Rain, Weex, J2 Capital,
  Zilliqa Group, Mirror, …).
- Magnitude is modest now only because just 396 of ~1065 passes are claimed this
  far from the event; it grows automatically as people personalize passes before
  June 2–3.

### Check-ins columns
`checkinId, displayableOrderNumber, fullPrice, qrCode, checkedInInBackstage,
firstName, lastName, birthdate, email, phone, sex, address, city,
countryIso3Code, nationalityIso3Code, companyName, jobTitle, guardian*,
createdAt`

No pass-name column — ticket type is recovered by joining to `orders` (below).

## Architecture

New module **`app/services/checkins_sync.py`**, mirroring `extasy_sync.py` and
**importing** its shared helpers rather than duplicating them:
`_fetch_csv`, `_map_ticket_type`, `_parse_extasy_dt`, `_record_sync_status`,
`_tier_index`, `TEST_BUYER_NAME_PATTERNS`, `TICKET_TYPE_MAP`, `_infer_company`,
`EXTASY_BASE`, `EXTASY_EVENT_ID`, `_CONNECTION_ERRORS`.

Adds:
```python
CHECKINS_URL = f"{EXTASY_BASE}/checkins/{EXTASY_EVENT_ID}"
```

Entry point: `async def sync_checkins_to_db() -> dict`.

### Pass-type resolver
1. Fetch `ORDERS_URL` once. Build `order_pass = {orderNumber: {qrCode: ticketName}}`
   and `order_single = {orderNumber: ticketName}` (when the order has exactly one
   distinct ticket name).
2. For each check-in resolve in priority order:
   - `order_pass[displayableOrderNumber][qrCode]` (qr-exact),
   - `order_single[displayableOrderNumber]` (single-type order),
   - first ticket name on the order (fallback),
   - else `DELEGATE`.
3. Map the resolved name through `TICKET_TYPE_MAP` (default `delegate`).

Verified: this resolves a pass for 100% of current check-ins (377 qr-exact,
19 single-type).

### Per-row upsert (existing-wins; per-row savepoint, same as extasy_sync)
For each check-in, after building `name`, `email` (lowercased/stripped),
`company` (`companyName`, else domain-inferred), `title` (`jobTitle`),
`country_iso3`, `ticket_bought_at` (`createdAt`), `ticket_type`, and a
`checkin` block:

```python
checkin_block = {
    "checkin_id":   checkinId,
    "order_number": displayableOrderNumber,
    "qr_code":      qrCode,
    "ticket_name":  resolved_pass_name,
    "phone":        phone or None,
    "city":         city or None,
    "country":      countryIso3Code or None,
    "full_price":   fullPrice or None,
    "synced_at":    <utc isoformat>,
}
```

- **Skip** if: name matches `TEST_BUYER_NAME_PATTERNS`; email blank; email
  already in `seen_emails` (intra-batch dedup, keep first).
- **Existing email (~337):**
  - Backfill **only blank** scalar columns: `company`, `title`, `country_iso3`,
    `ticket_bought_at`. Never overwrite a populated value.
  - `ticket_type`: **upgrade only** when `_tier_index(new) > _tier_index(existing)`.
  - `enriched_profile`: existing-wins merge, then always overwrite the
    `checkin` sub-key (authoritative per-attendee snapshot, like `.extasy`).
  - Count as `backfilled` (or `upgraded` if tier rose); else `skipped`.
- **New email (~44):** INSERT a new `Attendee` with the real `name`, `email`,
  `company`, `title`, `ticket_type`, `country_iso3`, `ticket_bought_at`, and
  `enriched_profile = {"source": "checkin", "checkin": checkin_block}`. Track
  the new id. (No `magic_access_token` on insert — it stays NULL and is minted
  on demand, exactly as extasy-sourced rows behave.)

### Make new people matchable immediately
After the batch, for each newly-inserted attendee id, fire
`app/services/profile_pipeline.run_full_enrichment(attendee_id)` **detached**
(same pattern as the sponsor-invite join): Grid + website enrich → AI summary →
embedding → match generation. New people are matchable within minutes rather
than waiting for the nightly enrichment sweep / match refresh.

## Cadence, observability, admin trigger

- **Daily cron at 02:05 UTC**, immediately after `extasy_sync` (02:00) so the
  `orders` feed needed for the pass join reflects the same morning's data, and
  before match refresh (02:45) / enrichment sweep (03:00).
- Write a `checkins_sync` row to `sync_status` via `_record_sync_status` with
  stats `{total_fetched, distinct, inserted, backfilled, upgraded, skipped,
  errors}` so silent failures surface on the dashboard.
- Admin trigger endpoint mirroring `POST /dashboard/sync-extasy`
  (e.g. `POST /dashboard/sync-checkins`, admin-only) for on-demand runs.

## Resilience
- Wrap both CSV fetches in try/except → record `PARTIAL` status, never crash the
  cron.
- Per-row `begin_nested()` savepoint isolates a bad row from the batch.
- Re-raise `_CONNECTION_ERRORS` so a dead session is not miscounted as per-row
  errors (mirrors extasy_sync's hard-won behavior).
- `IntegrityError` on the insert race → log + count, reconcile next run.

## Testing
Pytest (`tests/test_checkins_sync.py`) with synthetic in-memory fixtures:
1. **New attendee** — check-in email absent from DB → inserted with pass type
   resolved from a matching order row and real `company`/`title` from the report.
2. **Backfill existing** — check-in email present with blank `title` and a
   populated `company` → `title` filled, `company` untouched.
3. **Tier upgrade only** — existing DELEGATE + check-in VIP → upgraded; existing
   VIP + check-in DELEGATE → unchanged.
4. **Skips** — test/QA name and duplicate email within the batch are skipped.
5. **Pass resolver** — qr-exact, single-type, and fallback paths each return the
   expected ticket name.

## Rollout
1. Land module + endpoint + cron registration + tests (all green).
2. Run a one-off backfill (admin endpoint or `python -m`): recovers the 44 new
   people and backfills the 337.
3. Verify: matchmaker count rises from 945 toward ~989; spot-check a recovered
   profile has correct pass type + company/title; confirm the `checkins_sync`
   `sync_status` heartbeat shows `ok`.
4. Commit code + docs together; push.

## Out of scope (YAGNI)
- Not attempting to close the full −150. The remainder is multi-ticket buyers
  whose guests have not yet claimed; the same daily sync absorbs them as claims
  arrive.
- No new auth/secrets (endpoint is open like existing feeds).
- No changes to the `orders`/`tickets` extasy_sync path.

## Decisions (confirmed with Shaun)
- Merge policy: **backfill missing on existing + insert new** (existing-wins).
- Ticket type: **join orders by order# + QR** (not blanket DELEGATE).
- Cadence: **one-off backfill now + daily cron**.
