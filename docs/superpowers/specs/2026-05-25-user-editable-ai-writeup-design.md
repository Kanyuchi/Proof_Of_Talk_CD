# User-Editable AI Write-Up — Design

**Date:** 2026-05-25
**Status:** Approved (design); pending implementation plan

## Problem

Every attendee has an AI-generated write-up (`attendees.ai_summary`) that is how they are
introduced to their matches (match cards, briefings, AI Concierge brief lines) and which
also feeds their match embedding. It is produced by `generate_ai_summary()` from the
attendee's profile + scraped/enriched data.

When the AI gets it wrong, the attendee has **no self-service way to fix it**:

- The Profile page (`frontend/src/pages/Profile.tsx`) shows the AI Summary **read-only**
  (lines ~309–312). Structured fields (name, company, title, goals, interests, socials,
  privacy) are already editable.
- Even editing structured fields does not reliably fix the write-up: `PUT /auth/profile`
  clears the embedding and fires `refresh_profile_matches` → `process_attendee`, which
  **regenerates `ai_summary` via GPT** (`matching.py:172`). So a user can't pin a correction.

Real case (2026-05-25): Pouneh Bligaard emailed the team that her write-up was "incredibly
inaccurate" (a wrong/outdated scraped LinkedIn About). It had to be corrected by hand. This
feature lets attendees fix it themselves.

## Goals

- Attendees can **edit their own write-up** directly on the Profile page.
- A user's edit **sticks** — the AI never silently overwrites it again.
- Attendees who never touch their write-up keep getting it **auto-improved** as enrichment lands.
- A **Regenerate** button drafts a fresh AI version from the current profile as a writing aid.
- The user's text **feeds matching** (embedding), not just display.

## Non-Goals (v1)

- Editing the write-up from the unauthenticated magic-link self-fill card (`/m/:token`).
  Authenticated Profile page only.
- Moderation/abuse tooling beyond a length cap (it's the user's own bio).
- Gating/flags — the feature is **on for all logged-in attendees** (decision: 2026-05-25).

## Approach (chosen: "pin flag")

Single source of truth remains `attendees.ai_summary`. A boolean flag records that the user
has taken control, and the generation pipeline respects it. Chosen over (a) storing pin state
in `enriched_profile` JSON (wrong home, hard to audit) and (b) a separate `user_summary`
column (forces every `ai_summary` consumer to learn a precedence rule — more touch points,
more risk).

## Data Model

Migration on `attendees`:

| Column | Type | Default | Purpose |
|---|---|---|---|
| `ai_summary_pinned` | boolean | `false` (NOT NULL) | When true, AI never auto-regenerates the summary |
| `ai_summary_edited_at` | timestamptz | null | Audit/support breadcrumb for when the user last edited |

Existing rows default to `ai_summary_pinned = false` (keep auto-improving).

## Backend

### 1. Pin guard — `MatchingEngine.process_attendee` (the crux)

`matching.py:172`, change:

```python
attendee.ai_summary = await generate_ai_summary(attendee)
```

to:

```python
if not attendee.ai_summary_pinned:
    attendee.ai_summary = await generate_ai_summary(attendee)
```

Everything else in `process_attendee` (intent tags, deal-readiness, ICP, embedding) still
runs unconditionally. Result: editing goals still refreshes intents/ICP/matches, and the
pinned `ai_summary` flows into the embedding composite. This one guard makes edits stick
across all paths: profile saves, the 02:45/03:00 UTC crons, and every `refresh_profile_matches`.

### 2. Editing — `PUT /auth/profile` (`auth.py` `update_profile`)

- Add `ai_summary` to the `allowed` field set.
- Handling when `ai_summary` is present in the payload:
  - **Non-empty** (after `strip()`): set `attendee.ai_summary = value`,
    `ai_summary_pinned = True`, `ai_summary_edited_at = utcnow()`.
  - **Empty** (`""` / whitespace) = "reset to AI": set `ai_summary_pinned = False`
    (leave the text; the pipeline regenerates it on the refresh this endpoint already fires).
- Validation: `strip()`; reject/truncate at **2000 chars** (raise 400 if over).
- The endpoint already sets `embedding = None` and fires `refresh_profile_matches`; with the
  guard in place, a pinned summary survives that refresh while the embedding rebuilds.

### 3. Regenerate — `POST /auth/profile/regenerate-summary` (new)

- Auth required. Loads the user's attendee, calls `generate_ai_summary(attendee)` from the
  current profile, returns `{ "ai_summary": "<draft>" }`.
- **Does not save** and **does not change** `ai_summary_pinned`. It only returns a draft for
  the textarea; the user reviews/tweaks, then Save (which pins).
- Rate-limited `@limiter.limit("10/minute")` (it's a GPT call).

## Frontend (`Profile.tsx`)

- Replace the read-only AI Summary `<p>` with an editable `<textarea>` bound to form state,
  pre-filled with the current `attendee.ai_summary`.
- Char counter against the 2000-char cap.
- "Regenerate with AI" button → `POST /auth/profile/regenerate-summary`, shows a loading
  state, fills the textarea with the returned draft (does not auto-save).
- Helper text: *"This is how you're introduced to your matches — edit it anytime. Your
  version is kept; the AI won't overwrite it."*
- `ai_summary` is included in the existing Save payload (`PUT /auth/profile`). No new save flow.
- Optional: a subtle "Edited by you" indicator when `ai_summary_pinned` is true (nice-to-have).

## Embedding / Matching

No new work. The embedding composite already includes `ai_summary`; the pin guard ensures the
user's text is what gets embedded on every refresh. Editing goals/interests still rebuilds the
vector (pinned summary + new fields). This generalizes the manual Pouneh correction.

## Edge Cases

- Empty submitted write-up → un-pin + regenerate (reset to AI).
- Over 2000 chars → 400 (client also prevents).
- A pinned user who never edits again: summary stays as written; profile/goal changes still
  update matches; they can hit Regenerate to refresh the draft.
- Anti-hallucination sparse-stub logic in `generate_ai_summary` is bypassed for pinned users
  (we never call it) — intended.
- `profile_data_quality` SPARSE/PARTIAL/GOOD (concierge field prompts) is unaffected — it keys
  off structured fields, not the summary. Out of scope.

## Testing

Backend (`backend/tests/`):
- `process_attendee` preserves `ai_summary` when `ai_summary_pinned=True`; regenerates when `False`.
- `PUT /auth/profile` with non-empty `ai_summary` sets text + `pinned=True` + `edited_at`.
- `PUT /auth/profile` with empty `ai_summary` sets `pinned=False`.
- `PUT /auth/profile` rejects > 2000 chars (400).
- `POST /auth/profile/regenerate-summary` returns a draft, does not persist, does not flip pin.

Frontend smoke:
- Edit write-up → Save → reload shows edited text.
- Regenerate fills the box with a fresh draft; Save persists it.
- Edit goals + Save does **not** clobber a pinned summary.

## Rollout

1. Run the Alembic migration against prod Supabase **before merge** (per the prod smoke-test
   playbook), so the post-merge redeploy never hits missing columns.
2. Railway (backend) + Netlify (frontend) auto-deploy on merge.
3. Existing users remain un-pinned (auto-improving) until they choose to edit.

## Follow-ups

- After ship, set Pouneh Bligaard's `ai_summary_pinned = True` to lock her verbatim bio
  (`id=3bf5d2aa-f82f-4f37-8f41-36fdabbad20b`).
- Possible v2: allow write-up editing from the magic-link self-fill card.
