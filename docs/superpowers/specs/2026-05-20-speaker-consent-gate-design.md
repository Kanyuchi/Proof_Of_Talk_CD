# Speaker Consent Gate — Design

**Date:** 2026-05-20
**Status:** Approved (design), pending implementation plan
**Author:** Shaun + Claude

## Problem

Certain high-profile confirmed speakers (Franklin Templeton, BlackRock, Bank of
England, Mastercard, J.P. Morgan, Robinhood, State Street, Aave, Blockstream,
etc.) must **not** appear in the matchmaker until they have explicitly
consented to being included. In the master speaker sheet's
`2026 - Confirmed Speakers` tab, these are marked by an **orange (`#f9cb9c`)
background on the First Name cell (column B)** — **17 speakers** as of
2026-05-20.

**Live exposure today:** 16 of the 17 are already in the matchmaker DB and
matchable, and **8 are already surfacing in other attendees' live match lists**
(Arnaud Caudoux, Stani Kulechov, Jenny Johnson, Jacob Steeves, Johann Kerbrat,
Adam Back, Jack Mallers, Kim Hochfeld). This is an active reputational risk that
must be closed quickly.

## Scope

**In scope (this spec):** a consent gate that excludes the flagged speakers from
matching in both directions until consent is granted, plus an immediate data
action to close the current exposure.

**Out of scope (separate follow-up spec):** repointing the broken speaker sync
to the correct 2026 tabs (it currently reads the stale `OLD LIST OF SPEAKER`
tab), column remapping, and enrichment from the `2026 Form responses` tab. That
is tracked separately as "speaker data reconciliation."

## Decisions

- **Exclusion semantics:** *hidden both ways.* A gated speaker never appears as
  a match candidate to other attendees AND does not receive their own matches.
  They remain stored + enriched in the DB (dormant), fully reversible on consent.
- **Consent mechanism:** ops-controlled DB flag. Consent arrives via internal
  comms (Sneha confirms with each speaker → relays to Shaun). No self-consent
  app flow, no sheet-formatting coupling.
- **Detection:** the orange `#f9cb9c` background on column B of the
  `2026 - Confirmed Speakers` tab (gid `1622429203`), read via the Google Sheets
  API with `effectiveFormat.backgroundColor`. Confirmed detectable; yields
  exactly the 17.

## The 17 (as of 2026-05-20)

Arnaud Caudoux (BPI France), Stani Kulechov (Aave), Jenny Johnson (Franklin
Templeton), Caroline Pham (MoonPay), Jacob Steeves (Bittensor), Tom Lee
(Bitmine — *not yet in DB*), Emma Landriault (J.P. Morgan), Johann Kerbrat
(Robinhood), Ken Moore (Mastercard), Michael Arrington (Arrington Capital),
Adam Back (Blockstream), Xiao-Xiao J. Zhu (Jupiter), Nikhil Sharma (BlackRock),
Sasha Mills (Bank of England), Alex Kim (Upbit), Jack Mallers (Twenty One
Capital / Strike), Kim Hochfeld (State Street).

## Design

### 1. Data model

New column `attendees.matching_consent` — plain `String`, default
`not_required` (deliberately not a Postgres enum, to avoid the enum-migration
friction hit when `TEAM` was added to `ticket_type`).

| Value | Meaning | Matchable? |
|---|---|---|
| `not_required` | Normal attendee — never needed consent (default for all existing rows) | Yes |
| `pending` | Flagged high-profile speaker, awaiting consent | **No (gated)** |
| `granted` | Consent received | Yes |
| `declined` | Speaker said no | **No (gated)** |

One Alembic migration adds the column with server default `not_required`.

### 2. Exclusion points (mirror `staff_filter`)

Single predicate, e.g. in `app/services/consent_filter.py` (or alongside
`staff_filter`):

```python
def is_match_gated(attendee) -> bool:
    return (getattr(attendee, "matching_consent", "not_required") or "not_required") in ("pending", "declined")
```

Applied at the same two boundaries that govern who participates in matching:

- **Candidate side** — in `MatchingEngine._is_candidate_eligible`
  ([matching.py:226](../../../backend/app/services/matching.py)), add
  `if is_match_gated(candidate): return False` next to the existing
  `is_internal_staff` check. → gated speakers never surface in anyone's matches.
- **Subject side** — in `generate_matches_for_attendee` (and the
  `refresh_matches_for_new_attendees` loop), early-return if
  `is_match_gated(attendee)`. → gated speakers don't get their own match list
  generated.

### 3. Seeding (one-time) — `scripts/seed_speaker_consent.py`

Reads the `2026 - Confirmed Speakers` tab via the Sheets API, finds column-B
cells with background `#f9cb9c`, name-matches them to DB attendee rows, and sets
`matching_consent = 'pending'`. Idempotent. Prints a report: which of the 17
matched and were set, which didn't (e.g. Tom Lee, not yet in DB — logged so he's
gated if/when added).

### 4. Grant mechanism — `scripts/set_speaker_consent.py`

CLI for the ops trickle of confirmations:
- `--list` → show all `pending` / `granted` / `declined` speakers
- `--name "Stani Kulechov" --status granted` → flip a speaker
- On `granted`, the next match refresh (or an optional immediate per-attendee
  regen) brings them into matching.

Tiny volume (≤17, one at a time) makes a CLI sufficient. An admin-dashboard
toggle is a possible later add, not required for v1.

### 5. Phase 0 — close the live exposure immediately (data-only)

Independent of the code deploy (which is currently stalled by a Railway build
incident), because it's pure data:

1. Run the seed script → the 17 set to `pending`.
2. Scrub existing matches: delete `matches` rows where either side is gated →
   removes the 8 currently-live high-profile matches at once.

After the code-level filter deploys, gated speakers stay out automatically; this
Phase 0 just protects the window before/around the deploy.

## Testing

- **Unit:** `is_match_gated` → True for `pending`/`declined`, False for
  `granted`/`not_required`/missing.
- **Integration:** a `pending` attendee (a) never appears in any other
  attendee's candidate set, and (b) gets no matches generated for themselves;
  after flipping to `granted` + refresh, they participate normally.
- **Seed:** dry-run reports 16/17 matched (Tom Lee absent), 0 false matches.

## Risks & notes

- **Name matching in the seed** must be conservative (exact normalized
  first+last) to avoid gating the wrong person; unmatched names are reported, not
  guessed.
- **Tom Lee** is not in the DB; he'll be gated when the data-reconciliation
  follow-up (or any sync) adds him, provided that path also respects the orange
  flag — note this dependency in the reconciliation spec.
- The orange set can grow; re-running the seed picks up newly-flagged names
  without disturbing already-`granted` rows (seed only sets `not_required →
  pending`, never downgrades `granted`).
