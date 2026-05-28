# Priority Intro Requests — Design Spec

**Status:** Approved 2026-05-28, awaiting implementation plan
**Trigger:** Elliptic Gold-tier sponsor perk. Each Elliptic attendee has a curated "requested intros" list from a Google Sheet (one tab per requester: Aylin, Ylli, Oliver, ...). William layers human-mediated soft intros on top of what the system surfaces.

## Goal

Surface per-attendee priority intro requests at the top of the requester's match list, with honest factual cards (no GPT-fabricated synergy). Track acceptance with audit-grade timestamps so we can report perk ROI back to Elliptic and any future sponsor granted this perk.

## Non-goals

- Generalisation rollout to other sponsors (mechanism is generic, but Elliptic is the only client day-1; rollout is a follow-up).
- William's ops dashboard. He queries Supabase directly until a real need emerges.
- Attendee-facing "add this person to my request list" UI. v1 is operator-ingested only.
- Notifying William on target accept/decline. Polling for now.

## Data model

### New table: `requested_intros`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `uuid.uuid4` default |
| `requester_attendee_id` | UUID, FK -> attendees(id) | Indexed |
| `target_attendee_id` | UUID nullable, FK -> attendees(id) | NULL when target isn't in our DB yet |
| `target_name_raw` | TEXT | From sheet, for fuzzy-match audit and "not yet attending" cards |
| `target_company_raw` | TEXT nullable | From sheet, for fuzzy-match audit |
| `source` | TEXT | Provenance, e.g. `elliptic_sheet_2026_05_28` |
| `added_at` | TIMESTAMP | When ingested |
| `resolved_at` | TIMESTAMP nullable | Set when `target_attendee_id` is filled in by a later sheet re-ingest after the person registers |

Idempotency key on ingest: `(requester_attendee_id, target_name_raw, target_company_raw)`. Re-running the ingest script must not duplicate rows.

### Migration: `matches` table — accepted timestamps

Add two nullable columns, mirroring existing `deferred_a_at`/`deferred_b_at`:

- `accepted_a_at TIMESTAMP NULL`
- `accepted_b_at TIMESTAMP NULL`

Backfill is NULL. Historical accepted matches stay timestampless (no useful inference). New accepts set the column at the moment of transition `status_X` -> `"accepted"` in `update_match_status`.

## Matching pipeline change

In `MatchingEngine.generate_matches_for_attendee` (backend/app/services/matching.py):

1. Standard top-N retrieval runs first (existing curated + deep tiers unchanged).
2. After candidate set is built, load `requested_intros` for this `attendee_id` (cap 50).
3. For each target in the list:
   - **Target already in candidate set:** mark its `Match` row with `tier="priority_intro"`. The frontend renders sections in tier order (`priority_intro` → `curated` → `deep`), so the tier change alone is what floats it to the top. The existing similarity/complementary/overall scores are preserved (they're real and worth keeping for the explanation card).
   - **Target NOT in candidate set, but target_attendee_id IS NOT NULL:** force-add a new `Match` row with `tier="priority_intro"`. Set `similarity_score=0.0`, `complementary_score=0.0`, `overall_score=0.0` (the cards don't display these). `explanation` uses an honest factual template — NO GPT-4o call.
   - **target_attendee_id IS NULL (not in our DB):** skip from matching. Surfaced on the UI side from `requested_intros` directly as a greyed-out "Not yet attending" card.
4. Per-attendee total cap on `priority_intro`-tier rows: **50** (matches `SPONSOR_DEEP_POOL_SIZE`).

### Honest explanation template (no GPT)

```
You asked your concierge to introduce you to {target_first_name}.
They're attending Proof of Talk 2026.

Their focus: {target.goals or target.ai_summary[:200] or "Profile incomplete"}
{William may reach out to set up a soft intro.}
```

Rendered as plain text in `Match.explanation`. No fabricated synergy claims. If the target's profile is sparse, the card honestly says so.

## API changes

### `MatchResponse` (matches.py schemas)

Add field `tier: str` (already exists from deeper-match-pool). Frontend filters by tier to render the priority section.

Add field `priority_intro_meta: dict | None` populated only when `tier == "priority_intro"`:
- `requested_at` (= `requested_intros.added_at`)
- `target_in_db` (bool)
- `concierge_note` (str | None, future-proofing)

### New endpoint: `GET /matches/m/{token}/priority-intros` and `GET /matches/priority-intros`

Returns the requester's `requested_intros` rows — including unresolved (`target_attendee_id IS NULL`) entries — so the UI can render greyed-out "Not yet attending" cards for people who haven't registered yet. Two endpoints (magic-link + authenticated) mirror existing patterns.

## UI changes

### `MyMatches.tsx` and `MagicMatches.tsx`

New section at the top of the matches list, BEFORE the curated tier:

```
Your priority intros (N)
From your concierge request. William may reach out about these.

[match card 1]
[match card 2]
...
```

- Match cards render normally for resolved targets (accept/decline/schedule flow identical to existing matches; uses new `accepted_*_at` on transition).
- Unresolved targets ("Not yet attending") render a greyed card with name/company/status only — no actions.
- Section is hidden entirely if the attendee has no `requested_intros` rows.

## Ingest

New script `backend/scripts/ingest_requested_intros.py`:

- Input: Google Sheet (CSV export at first, gspread later if needed). One tab per requester, sheet ID `1g40iZM_utxjG_aPzynDmOwny8g_iQKv0FAHyj6RWE5I`.
- Per-tab:
  - Parse rows (column mapping confirmed against actual sheet — placeholder schema: `Name | Company | Notes`)
  - Fuzzy-match `Name + Company` against `attendees.name + attendees.company` (rapidfuzz, ≥85 token-set-ratio threshold)
  - On match: upsert `requested_intros` with `target_attendee_id` filled
  - On miss: upsert `requested_intros` with `target_attendee_id=NULL`, `target_name_raw` and `target_company_raw` set
- Idempotent on `(requester_attendee_id, target_name_raw, target_company_raw)`
- CLI flags: `--dry-run` (default), `--confirm`, `--sheet-csv PATH`, `--requester-email EMAIL`
- Output: stdout summary (rows ingested per tab, hit/miss counts) + JSON report of all misses for ops review

After ingest, the operator must trigger a match refresh for each requester to surface the new priority intros immediately:

```bash
python -c "
import asyncio
from app.services.profile_pipeline import refresh_profile_matches
asyncio.run(refresh_profile_matches(<aylin_id>))
"
```

Or hit the existing admin endpoint that does the same.

## Reciprocity / accepted timestamps

`update_match_status` in `app/api/routes/matches.py`:

- When `status_a` transitions `pending` -> `accepted`, set `accepted_a_at = now()`.
- Same for `status_b` / `accepted_b_at`.
- No change to existing reciprocity-loop cron behaviour — it only checks `status_a == status_b == "accepted"`.
- Reports (e.g. future "How many Elliptic targets accepted?") query `accepted_a_at IS NOT NULL` joined with `requested_intros` by `target_attendee_id`.

## Testing

New tests:

- `tests/test_requested_intros_ingest.py`: fuzzy-match logic, idempotency, miss handling.
- `tests/test_matching_priority_intros.py`:
  - Requester with target already in candidate pool → tier upgraded to `priority_intro`, score boosted.
  - Requester with target NOT in candidate pool → force-added row with `priority_intro` tier and factual explanation, no GPT call (mocked).
  - Cap at 50 enforced.
  - Targets with `target_attendee_id=NULL` skipped at the matching layer.
- `tests/test_matches_accepted_timestamps.py`: status_a transition `pending` → `accepted` stamps `accepted_a_at`; status_b separately; verify the existing `update_match_status` route does NOT also stamp on transitions to `declined`/`met`/other states.
- `tests/test_matches_priority_intro_endpoint.py`: magic-link + authed endpoints return resolved + unresolved entries correctly.

Existing matching tests must continue to pass — priority intros are additive.

## Migration

Alembic migration:

1. Create `requested_intros` table with the columns above + indexes on `requester_attendee_id` and `target_attendee_id`.
2. Add `accepted_a_at` and `accepted_b_at` to `matches`.

Both columns default NULL; no data migration needed.

## Rollout

1. Apply migration to prod Supabase.
2. Deploy backend.
3. Operator gets the Elliptic sheet (either share with shaunkudzi@gmail.com, switch Claude Drive connector to shaun@proofoftalk.io, or drop CSV in `backend/data/elliptic_targets.csv`).
4. Confirm sheet column structure matches the ingest script's expected schema; adjust column mapping if needed.
5. Run `python scripts/ingest_requested_intros.py --sheet-csv backend/data/elliptic_targets.csv --confirm`.
6. Run match refresh for each requester (Aylin, Ylli, Oliver).
7. Spot-check the requesters' magic links or logged-in `/matches` — priority intros section renders correctly.
8. Tell William the data is live; he begins soft intros.

## Open items / follow-ups (deferred, NOT in this PR)

- William's ops dashboard (cross-attendee target × status grid).
- Email/Slack notification to William when a target accepts.
- Generalise to non-Elliptic sponsors (mechanism is already generic; rollout is just ingest + refresh).
- Attendee self-service: let an attendee mark someone as "I want to meet them" from a profile preview.

## Spec review notes

- Sheet column mapping is a placeholder (`Name | Company | Notes`). Real columns confirmed at ingest-time once sheet is shared. Script's column parser is the only thing that needs adjustment then — the data model and matching changes are sheet-agnostic.
- "William" referenced throughout — assumed to be the PoT team member who'll handle soft intros (the user named him in conversation). No code wiring to William specifically; the design accommodates any human-mediated layer above the surfaced data.
- `priority_intro` tier sits above `curated` in the rendering order but the existing `tier` column is reused, no new enum.
