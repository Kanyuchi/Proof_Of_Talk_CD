# AI Concierge — Proactive Field Drafting

**Date:** 2026-05-13
**Status:** Approved (design); pending implementation plan
**Owner:** Shaun
**Source:** `whats_next.md` → Soon → "AI Concierge offers to draft missing fields" (item #5)
**Estimate:** 1.5–2 hours

---

## Goal

When an attendee opens the AI Concierge with an incomplete profile, the assistant proactively offers to draft a high-impact missing field. The user accepts → GPT-4o generates 2–3 candidates → user picks one, edits it inline, hits Save → field is persisted, embedding regenerates, match refresh is kicked off in the background.

This closes the **self-enrichment loop** started by the 2026-05-13 work (locked-match preview + match-quality benchmark on `MyMatches`), where the matchmaker now *shows* attendees the cost of an incomplete profile but doesn't yet offer to fix it for them. This spec is the fix-it side.

---

## Non-Goals

- Photo upload nudge — separate affordance, no GPT draft required, no match-quality impact.
- Magic-link / unauthenticated concierge access — current `useChat` is authenticated-only and the offer flow inherits that constraint. Magic-link users get the existing welcome message.
- Notifying the user when matches actually refresh — rely on the existing Mutual Match nav badge cycle.
- Multi-language support — English only, matching the rest of the platform.

---

## User Flow

1. Attendee opens the AI Concierge (chat widget or `/concierge`).
2. `ChatPanel` mounts → `useChat` fetches persisted history AND calls a new `GET /chat/profile-prompt` endpoint.
3. Backend computes profile completeness, looks up `enriched_profile.field_prompts` state, returns the next field worth offering — or `null` if all six tracked fields are full / all candidate fields are recently declined.
4. **If `null`** → standard welcome + suggested-prompts list (current behaviour).
5. **If `{field: "goals", current_completeness_pct: 60}`** → tailored welcome:
   > *"Your profile is 60% complete — I can draft your conference goals based on your title at Coinbase. Want me to?"*
   with two chips: `[ Yes, draft my goals ]` and `[ Maybe later ]`.
6. **On Yes** → `POST /chat/draft-field {field}` → assistant message renders 3 candidate chips below. Click any chip → opens an inline `<textarea>` pre-filled with the candidate text + Cancel / Save buttons.
7. **On Save** → `POST /chat/save-field {field, value}` → optimistic confirmation:
   > *"Saved! I've kicked off a match refresh in the background — new recommendations will appear shortly."*
   Backend fires `BackgroundTasks` to regenerate the embedding and refresh matches.
8. **On Maybe later (decline) or Cancel** → `POST /chat/decline-prompt {field}` → assistant: *"No problem, you can edit it anytime from your Profile."* + suggested prompts render below as a fallback.

---

## Architecture

### Backend

**4 new endpoints in `backend/app/api/routes/chat.py`** (auth required, current user's attendee_id is the subject):

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/chat/profile-prompt` | — | `{field, current_completeness_pct} \| null` |
| POST | `/chat/draft-field` | `{field}` | `{candidates: [str, str, str]}` (2 if SPARSE) |
| POST | `/chat/save-field` | `{field, value}` | `{ok: true}` (fires background re-embed + match refresh) |
| POST | `/chat/decline-prompt` | `{field}` | `{ok: true}` |

**2 new helpers in `backend/app/services/concierge.py`:**

```python
def select_next_field_to_offer(attendee: Attendee) -> str | None:
    """Returns 'goals' | 'target_companies' | 'interests' | None
    based on field emptiness + enriched_profile.field_prompts state."""

async def draft_field_candidates(field: str, attendee: Attendee) -> list[str]:
    """GPT-4o drafts 2-3 candidate values for the given field, grounded
    in name + title + company + ai_summary + linkedin.headline.
    Returns 2 candidates (with a 'starting point' hint) for SPARSE profiles,
    3 otherwise."""
```

**New schemas in `backend/app/schemas/chat.py`:** `ProfilePromptResponse`, `DraftFieldRequest`, `DraftFieldResponse`, `SaveFieldRequest`, `DeclinePromptRequest`. All trivially Pydantic.

### Frontend

**4 new API client functions in `frontend/src/api/client.ts`:**
`getProfilePrompt()`, `draftField(field)`, `saveField(field, value)`, `declinePrompt(field)`.

**`useChat` hook update:** add `profilePromptOffer` state, fetch on mount alongside history. Expose `acceptPrompt`, `declinePrompt`, `saveDraftedField` actions.

**New component `frontend/src/components/chat/ProfilePromptOffer.tsx`:**
Encapsulates the offer UI. Three internal states:
- `idle` — tailored welcome message + Yes/Maybe-later chips.
- `picking` — three candidate chips after draft loads.
- `editing` — one chip clicked → inline `<textarea>` pre-filled + Cancel/Save.
- `saved` — confirmation card with subtle background-refresh note.

**`ChatPanel.tsx` update:** in the empty-history branch, render `<ProfilePromptOffer>` instead of the existing static welcome when `profilePromptOffer != null`. After save or decline, render the standard suggested-prompts list below so the user has somewhere to go next.

### Match Refresh

`save-field` calls `BackgroundTasks.add_task` with a wrapper that:
1. Regenerates `composite_text` and `embedding` for this attendee (reusing the embedding logic in `app/services/embeddings.py` or `enrichment.py` — whichever currently owns the composite text builder).
2. Calls `matching.generate_matches_for_attendee(attendee_id)`.

Non-blocking from the user's POV. Failures are logged and don't surface to the chat UI — the daily 02:45 UTC refresh cron is the fallback.

---

## Data Model

### `attendee.enriched_profile.field_prompts` (new JSONB sub-key)

```json
{
  "field_prompts": {
    "goals": { "state": "declined", "last_offered_at": "2026-05-13T20:11:00Z" },
    "target_companies": { "state": null, "last_offered_at": null },
    "interests": { "state": "accepted", "last_offered_at": "2026-05-13T20:08:00Z" }
  }
}
```

**State machine:**
- `null` → never offered. Eligible.
- `"declined"` → user said Maybe later or Cancel. Re-eligible **30 days** after `last_offered_at`.
- `"accepted"` → user saved a value. The field itself will now be non-empty, so the offer naturally skips it. State acts as an audit trail, not a gate.

No new column required — reuses the existing `enriched_profile` JSONB. The JSONB mutation tracking fix shipped earlier (see `whats_next.md` Done ✓) ensures these writes persist.

### Completeness denominator (6 fields)

| Field | Weight |
|---|---|
| `goals` | 1 |
| `target_companies` | 1 |
| `interests` | 1 |
| `title` | 1 |
| `company` | 1 |
| `photo_url` | 1 |

Completeness = filled / 6. Offer fires when completeness < 80% (i.e. **4 of 6 or fewer** non-empty — equivalently, at least 2 fields missing) **AND** there exists at least one offerable field in `{goals, target_companies, interests}` that is empty and not recently declined.

Note: an attendee with `title + company + photo_url + one of {goals|target_companies|interests}` filled = 4/6 = 67% → still fires. An attendee with 5/6 filled = 83% → no longer offered. This keeps the offer high-signal: by 5/6 the profile is good enough to produce reasonable matches.

`title` and `company` are part of the denominator (so an attendee with a full title+company already gets a higher baseline) but are NOT offered for drafting — those come from registration/Extasy and aren't appropriate to GPT-generate.

---

## Selection Logic — `select_next_field_to_offer`

```
priority = ["goals", "target_companies", "interests"]
for field in priority:
    value = getattr(attendee, field)
    if value is non-empty: continue
    state = enriched_profile.field_prompts.get(field, {})
    if state.get("state") == "declined":
        if last_offered_at within 30 days: continue
    return field
return None
```

This ensures we always offer the highest-impact missing field that the user hasn't recently turned down.

---

## GPT Prompt — `draft_field_candidates`

**Input context (always):** name, title, company, vertical_tags, ai_summary, enriched_profile.linkedin.headline.

**Per-field prompts:**

- **goals** — "Draft 2-3 conference goals this attendee might want at Proof of Talk 2026 (a Web3 event of 2,500 decision-makers). Goals should be concrete and action-oriented (e.g. 'Meet 5 LPs interested in early-stage Web3 infrastructure funds'). Return JSON: `{candidates: [str, str, str]}`."
- **target_companies** — "Suggest 2-3 specific companies attending Proof of Talk this person should prioritise meeting, given their role. Return JSON: `{candidates: [str, str, str]}`." (Pulls candidate companies from the same attendee context passed to the main concierge — `_list_attendees`.)
- **interests** — "Suggest 2-3 Web3 sectors or topics this attendee likely follows professionally. Return JSON: `{candidates: [str, str, str]}`."

**SPARSE-profile detection — single source of truth:** reuse the existing logic in `concierge._brief_attendee_line`:
```python
completeness = sum([
    bool(a.interests),
    bool(a.goals and a.goals.strip()),
    bool(a.intent_tags),
    bool(a.title and a.title.strip()),
])
is_sparse = completeness <= 1
```
Extract this into a `profile_data_quality(attendee) -> Literal["SPARSE", "PARTIAL", "GOOD"]` helper in `concierge.py` and call it from both `_brief_attendee_line` and `draft_field_candidates`.

When `is_sparse`: return 2 generic candidates with the prompt instruction *"Mark these as starting points — the user has limited profile data and may need to rewrite."* Frontend shows the candidates with a subtle "Starting points — feel free to rewrite" hint above them.

**Anti-hallucination:** model temperature 0.5; system prompt explicitly forbids inventing companies, fund sizes, or theses not present in the input. Same posture as the existing `generate_ai_summary` guardrails.

---

## Edge Cases

| Case | Behaviour |
|---|---|
| Profile already ≥ 80% complete | Endpoint returns `null` → standard welcome shown. |
| All three offerable fields declined within 30 days | Endpoint returns `null` → standard welcome. |
| User saves an empty string | Backend rejects (400) → toast: "Looks empty — try a few words." |
| GPT returns malformed JSON | Endpoint returns 500 + frontend shows: "Couldn't draft suggestions right now. Try filling this in from your Profile page." |
| User declines, then later edits the field from `/profile` | The field's `state` stays `declined` but `value` is non-empty, so selection naturally skips it. No re-prompt. |
| Concurrent saves (two tabs) | Last write wins. `last_offered_at` is informational only, not a lock. |
| Embedding regeneration fails in background | Logged; daily 02:45 UTC refresh is the fallback. User never sees the error. |

---

## Files Touched

**New:**
- `frontend/src/components/chat/ProfilePromptOffer.tsx`

**Edited:**
- `backend/app/api/routes/chat.py` — 4 new endpoints
- `backend/app/services/concierge.py` — 2 new helpers + GPT prompts
- `backend/app/schemas/chat.py` — 5 new request/response schemas
- `frontend/src/api/client.ts` — 4 new fetch functions
- `frontend/src/hooks/useChat.ts` — `profilePromptOffer` state + actions
- `frontend/src/components/chat/ChatPanel.tsx` — render `ProfilePromptOffer` in empty-history branch
- `frontend/src/types/index.ts` (or equivalent) — `ProfilePromptResponse` type

No new dependencies. No DB migration (JSONB sub-key only).

---

## Testing

**Backend (pytest):**
- `select_next_field_to_offer` covers: all-empty → goals; goals filled → target_companies; goals declined < 30d → target_companies; goals declined > 30d → goals; all filled → None; all declined recently → None.
- `draft_field_candidates` returns 3 candidates for a populated profile, 2 for a SPARSE profile, raises on GPT failure.
- `POST /chat/save-field` updates the attendee row AND schedules the background re-embed (mock `BackgroundTasks`).
- `POST /chat/decline-prompt` writes the correct JSONB shape.

**Frontend (manual smoke test, per project convention):**
- Login as an attendee with empty `goals` → open chat → see tailored welcome → click Yes → see 3 chips → click one → see textarea → edit → Save → see confirmation.
- Reload chat → second-priority field (`target_companies`) now offered.
- Decline a prompt → reload → standard welcome shown (until 30 days pass or another field becomes offerable).
- Attendee with all six fields filled → standard welcome, no offer.

---

## Open Questions

None at design time. All earlier forks resolved during brainstorming (offer surface, fields in scope, save UX, persistence model, completeness denominator, immediate re-embed vs cron-only).

---

## Out-of-Scope Follow-Ups (not for this spec)

- Photo upload nudge as a separate offer type (no GPT draft step).
- Magic-link concierge access + offer flow.
- A periodic email-side reminder for declined fields.
- An admin dashboard tile showing offer accept / decline conversion.
- "Refresh complete" toast on `MyMatches` when the background job finishes.
