# Deeper Match Pool with Enrichment-Gated Unlocking — Design

**Date:** 2026-05-21
**Status:** Approved (design). Implementation recommended in a fresh session.
**Author:** Shaun + Claude

## Problem / Motivation

Today each attendee sees only their curated AI matches (those scoring ≥ `MIN_MATCH_SCORE` = 0.60). Three product gaps:

1. **Too few profiles.** Attendees want more people to consider, not just the handful the AI surfaces. Target: ~10 more beyond the curated top.
2. **"Maybe later" is a dead end.** Deferring a match removes interest but surfaces nothing new — the pool only shrinks.
3. **No incentive to enrich.** Profile completeness drives match quality but the attendee sees no direct payoff. The incentive should be: **enrich your profile → unlock more profiles** (quantity-vs-quality lever).

## Goals

- Surface a deeper pool of ~20 ranked candidates per attendee (curated top + deeper tail).
- "Maybe later" instantly swaps in the next-best candidate; deferred profiles can resurface.
- Number of visible profiles scales with profile completeness (tiered), with a clear "complete your profile to unlock more" nudge.

## Non-Goals

- No separate "Discover / browse everyone" pool — the extra profiles are **deeper AI matches**, not a different surface (decision 2026-05-21).
- No new LLM spend in v1 (GPT-4o stays on the curated top only). Spending more / adding models to improve the deep pool is a **deferred conversation** after v1 ships.

## Design

### Part 1 — Candidate pool (source of the extra profiles)

Extend `services/matching.py::generate_matches_for_attendee` to persist **more** candidates, not just ≥ 0.60. Retrieve a larger pgvector neighbour set and tag each persisted `matches` row with a new **`tier`** column:

- `tier = "curated"` — top ~8: full GPT-4o rerank + natural-language explanation (today's behaviour, unchanged).
- `tier = "deep"` — next ~12: ranked by pgvector similarity + the existing deterministic rerank (`COMPLEMENTARY_VERTICALS`, ICP keyword boosts). **No GPT call**, so no new LLM cost. Explanation field is empty or a light templated string.

A full pool is ~20 ranked candidates. Persist deep candidates down to a lower floor (e.g. ~0.45) — tune during implementation. The existing company-similarity fallback (≤3 sector peers when nothing clears threshold) stays as a last resort for very sparse pools.

### Part 2 — Tiered visibility (the enrichment incentive)

A **display-layer cap** based on the viewer's completeness tier, reusing `concierge.py::profile_data_quality()` (SPARSE / PARTIAL / GOOD) and the existing <80% completeness signal:

| Completeness tier | Profiles shown |
|---|---|
| SPARSE | top 5 |
| PARTIAL | top 10 |
| GOOD (≥80%) | full pool (~20) |

Caps applied where matches are served (`api/routes/matches.py`: authed `GET /matches/{id}` and magic `GET /matches/m/{token}`). Below GOOD, return a small payload field (e.g. `locked_count`, `next_tier_at`) so the frontend can show **"Complete your profile to unlock N more matches"**, wired to the existing Concierge `ProfilePromptOffer`.

### Part 3 — Maybe-later instant swap

Add per-viewer deferral, mirroring the existing two-sided `status_a`/`status_b` pattern on the `matches` row:

- New columns: `deferred_a_at TIMESTAMPTZ NULL`, `deferred_b_at TIMESTAMPTZ NULL`.
- Visible list computed dynamically: order = `[fresh (not deferred, not declined/accepted) by rank]` then `[deferred by deferred_at asc]`; take the tier `limit`.
- Tapping **"Maybe later"** stamps the viewer's `deferred_*_at = now()` → the card leaves the visible window and the next-best fresh candidate slides in. Deferred profiles resurface at the back once fresh ones are exhausted (so nothing is lost).
- New endpoint (authed + magic variants): `PATCH /matches/{id}/defer` (and `/matches/m/{token}/defer`). Verify how today's "Maybe later" control behaves first — it may currently set a status; repoint it to `defer`.

### Part 4 — Frontend

- `MyMatches.tsx` and `MagicMatches.tsx`: render the capped window; "Maybe later" calls the defer endpoint then refetches so the replacement appears instantly.
- Unlock nudge shown at SPARSE/PARTIAL tiers (reuse `ProfilePromptOffer` / Concierge entry point).
- `AttendeeMatches.tsx` (admin) shows the full pool with tier labels for visibility.

## Data Model Changes

- `matches.tier` — enum/text: `curated` | `deep` (default `curated` for back-compat).
- `matches.deferred_a_at`, `matches.deferred_b_at` — nullable timestamps.
- Alembic migration; backfill existing rows to `tier='curated'`, deferred = NULL.

## Verification Plan

- Unit: tier-cap function returns 5/10/20 for SPARSE/PARTIAL/GOOD; visible-ordering function puts deferred at the back; defer endpoint stamps the correct side.
- Integration: an attendee with a full pool sees 5 → 10 → 20 as completeness rises; "Maybe later" swaps in the next candidate and the deferred one reappears after the fresh queue empties.
- Manual: magic-link (anon) and logged-in both honour the cap and the swap. Smoke-test on a real attendee before deploy.

## Open / Deferred

- **Cost / models:** whether to GPT-explain the deep pool, bump the OpenAI budget, or add other models to improve the experience — revisit after v1 is live and observed (per Shaun, 2026-05-21).
- Tuning: exact deep-pool floor (~0.45), curated count (~8), and full-pool size (~20).

## Implementation Note

This touches the core matching pipeline. Recommend implementing from this spec in a **fresh session** (this design session ran long) via the writing-plans → executing-plans flow.
