# Sheets Sync — Supabase → PoT26 Master Email Database

One-way, hourly sync from the Supabase `attendees` table into Ferd's outreach Google Sheet so the outreach team can tell at a glance who has already signed up or bought a ticket and stop double-contacting them.

**Target Sheet:** `PoT26_Master_Email_Database_v3`
**Sheet ID:** `1L3SpraHSWDpTwEg2CiBQ3ytHT9mS5zvOljrtIABKw8Q`

## What the script does

The script lives as a bound Apps Script on the Sheet and creates/refreshes two tabs:

- **`POT Attendees`** — dedicated mirror of the Supabase `attendees_sync` view. The script creates this tab if missing and rewrites it on each run. Columns: `Email | Name | Company | Signed Up At | Ticket Type | Ticket Bought At`. `Ticket Type` is the signal that matters (`DELEGATE` / `VIP` / `SPEAKER`); if a row is in this tab, they've bought a ticket.
- **`POT Sync Log`** — appended with one row per successful run (`Timestamp | Rows synced | Note`). Use this to spot-check the sync is alive; if no new row has appeared for more than an hour, the sync has stopped.

**The script never writes to `MERGED - All Investors`** — that tab is owned by Ferd's existing `mergeInvestorTabs()` function which drops-and-rebuilds it on every run. Writing POT data directly into MERGED would get wiped. Downstream step (not yet shipped): add XLOOKUP columns in `MERGED - All Investors` that point at `POT Attendees` by email.

## Architecture

```
Supabase `attendees` table
        │
        └── public.attendees_sync view (6 columns, SELECT granted to anon)
                │
                │   REST GET /rest/v1/attendees_sync?select=...&limit=1000&offset=...
                │
                └── Apps Script `syncFromSupabase()` (hourly trigger)
                        │
                        └── POT Attendees tab  +  POT Sync Log tab
```

## Supabase prep (one-time)

Run in the SQL Editor (or via MCP `apply_migration`):

```sql
create or replace view public.attendees_sync as
select email, name, company, created_at, ticket_type, ticket_bought_at
from public.attendees;

grant select on public.attendees_sync to anon;
```

This exposes only the 6 columns the sync needs. The anon key can read nothing else in `attendees` — if the key ever leaks, the blast radius is 6 columns, not the whole profile including phone numbers, AI summaries, and embeddings.

## Apps Script installation

1. Open the Sheet → **Extensions → Apps Script**.
2. Add a new script file (the existing `Code.gs` already contains `mergeInvestorTabs` — add the sync as a second file or append to the existing file).
3. Paste the contents of `Code.gs` from this directory.
4. **Project Settings → Script Properties**, add:
   - `SUPABASE_URL` — `https://<project>.supabase.co`
   - `SUPABASE_ANON_KEY` — the **anon** public key (not `service_role`)
5. In the editor, pick `syncFromSupabase` from the function dropdown → **Run** → approve the OAuth consent prompt on first run.
6. Verify the new `POT Attendees` tab was populated and `POT Sync Log` has one entry.
7. Install the hourly trigger — either:
   - Click **Triggers** (alarm-clock icon) → **+ Add Trigger** → Function: `syncFromSupabase`, Event source: Time-driven, Type: Hour timer, Interval: Every hour, or
   - Run `installTrigger()` once from the editor (it replaces any existing trigger for `syncFromSupabase`).

## Operating notes

- **Rotating the Supabase key**: Script Properties → edit `SUPABASE_ANON_KEY` → save. No redeploy needed.
- **Pausing the sync**: Triggers panel → delete the `syncFromSupabase` trigger. Re-add when ready.
- **Troubleshooting**: run `syncFromSupabase` manually from the editor — it throws with a readable message on missing Script Properties, missing view, or 4xx/5xx from Supabase. The Execution Log shows the stack trace.
- **Schema changes**: if `attendees` grows a new column you want in the Sheet, update the `attendees_sync` view (drop + recreate) AND the `HEADERS` / `select=` / mapping in `Code.gs`. These must stay aligned.

## Out of scope (v1)

- **Attendance / check-in status** — `attendees` table has no `checked_in_at` column. Proposed for v2 once check-in flow exists.
- **Two-way sync (Sheet → Supabase)** — intentionally one-way; Ferd's manual edits stay in the Sheet only.
- **Syncing feeder tabs (`WARM - Ferdi Investors`, `COLD - *`)** — they roll up into `MERGED - All Investors` which is the operational view.
- **1000 Minds nominations** — the 1000 Minds app uses a separate `nominations` table in the same Supabase project (219 rows). A second `POT Nominees` sync following the same pattern would close the dedup gap for nominees, but is pending Ferd's decision.

## Related backend work

The Supabase `attendees` table is populated by `backend/scripts/ingest_extasy.py`. After the 2026-04-15 refactor that script is **idempotent** — it can be run or scheduled repeatedly without wiping enrichment data. Scheduling the ingest script is the logical next step that closes the last manual piece of Ferd's dedup loop.
