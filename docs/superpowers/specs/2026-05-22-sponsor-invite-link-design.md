# Sponsor self-service invite link + universal save-trigger — Design

**Date:** 2026-05-22
**Status:** Approved (design), pending implementation plan
**Author:** Claude (brainstormed with Shaun)

## Problem

Sponsors (and anyone we choose to invite) have no way to onboard themselves onto
the matchmaker. Today an attendee row must already exist — created from a
Rhuna/Extasy ticket or added by ops via the speaker sheet — before someone can
register; `POST /auth/register` is gated by `REQUIRE_TICKET_TO_REGISTER`.
Sponsors don't buy Rhuna tickets, so they can't get in without an operator
manually creating their row first.

We want a **single shared link** that anyone can open to create their own account
and profile, with no pre-existing row, and have their profile enriched and matched
automatically the moment they save — without an operator in the loop.

A second, related gap surfaced during design: the **Profile-page save does not
refresh matches immediately**. `PUT /auth/profile` only nulls the embedding and
waits for the nightly cron (03:00 enrichment sweep regenerates null embeddings,
02:45 match refresh). So the "enrich your profile to unlock better matches" loop
half-works — the tier *cap* (5/10/20) unlocks instantly because it is computed at
read time, but the *improved* matches from the new info lag until the next
morning. Only the AI Concierge save path regenerates immediately today.

## Goals

1. A shareable, reusable link — `https://meet.proofoftalk.io/join/<code>` — that
   lets anyone self-register a full login account with no pre-existing attendee row.
2. Everyone who joins via the link is tagged `ticket_type=SPONSOR`.
3. On join (cold start), run the **full** enrichment + matching pipeline in the
   background: Grid + company website + AI summary + embedding + match generation.
   LinkedIn is queued for the operator's next manual scrape pass (it cannot run
   automatically — see Non-Goals).
4. Make **every profile save, for everyone**, immediately refresh the embedding and
   matches (the light re-embed + rematch path the Concierge already uses), so the
   enrich-to-unlock loop closes in seconds instead of overnight.
5. Feature is **off by default** — blank invite code = endpoint and page both refuse.

## Non-Goals

- **Automatic LinkedIn scraping on save.** LinkedIn enrichment is operator-driven
  via the manual Playwright script (`scripts/linkedin_scrape.py`, browser login +
  2FA). The join flow cannot scrape LinkedIn synchronously. Instead, a joiner who
  supplies a `linkedin_url` automatically appears in the dashboard's pending-LinkedIn
  count (has `linkedin_url`, no LinkedIn enrichment yet) and is picked up by the next
  operator scrape pass. A Voyager-cookie best-effort fill-in runs only if
  `LINKEDIN_LI_AT_COOKIE` is set (it usually is not).
- **Per-recipient links, revocation, expiry, or usage analytics.** That is
  Approach B (a DB-backed `invite_links` table). Deliberately deferred — this spec
  ships one static shared link. Graduating to B later does not change the `/join`
  page or the enrichment triggers; only where the code is validated changes.
- **Passwordless onboarding.** The link creates a real email+password login
  ("create their own accounts").
- **Re-scraping Grid/website on every profile edit.** Profile saves use the light
  path (typed fields → embedding). A full re-scrape only happens on cold-start join,
  or when a save introduces a new company/website/linkedin_url that is not yet
  enriched (see Optional escalation).

## Approach (chosen: A — static env invite code)

Considered three approaches:

| | A — Static invite code (env var) | B — DB-backed invite links | C — Passwordless magic profile |
|---|---|---|---|
| The link | One URL, code is an env var | Many URLs, dashboard CRUD | One URL, emails a magic link |
| Account | Full login | Full login | No password |
| Revoke/expire/stats | Rotate env (1 redeploy) | Per-link, no redeploy | n/a |
| Build size | Small | Large (migration + CRUD + UI) | Medium |

**Chosen A** — delivers exactly "one shared link anyone can use" with the smallest
surface. The real new logic (the enrichment triggers) is identical across all three,
so A spends effort only where it is needed. B is a clean later upgrade on top of A.

## Architecture

### Config

New setting in `app/core/config.py`:

```python
# Sponsor self-service invite. Blank = feature OFF (the /join endpoint and page
# both refuse). Set to an unguessable string (e.g. secrets.token_urlsafe(24))
# in Railway env, then share https://meet.proofoftalk.io/join/<code>.
SPONSOR_INVITE_CODE: str = ""
```

`.env.example` gains `SPONSOR_INVITE_CODE=` with a comment. CLAUDE.md documents it.

### Backend — `POST /auth/join`

New endpoint beside `register` in `app/api/routes/auth.py`, rate-limited
`@limiter.limit("5/minute")`. New schema `JoinRequest` in `app/schemas/auth.py`
(same profile fields as `RegisterRequest`, plus `invite_code`, reusing the shared
password-strength + non-blank-name validators).

`JoinRequest` fields: `invite_code`, `email` (EmailStr), `password`, `name`,
`company`, `title`, `linkedin_url`, `twitter_handle`, `company_website`, `goals`,
`target_companies`, `interests`, `seeking`, `preferred_geographies`, `deal_stage`,
`privacy_mode`.

Logic:

1. **Validate code.** If `SPONSOR_INVITE_CODE` is blank → 403 (feature off). Else
   `secrets.compare_digest(data.invite_code, settings.SPONSOR_INVITE_CODE)` —
   constant-time. Mismatch → 403 "This invite link is invalid or expired."
2. **Existing login guard.** If a `User` already exists at this email → 400
   "Email already registered — please log in instead."
3. **Create-or-merge attendee.** Extract the existing merge block from `register`
   (auth.py:67-119) into a shared helper `_upsert_attendee_from_payload(db, data,
   default_ticket_type)` used by both `register` and `join`. For join, force
   `ticket_type="SPONSOR"` server-side (the client cannot choose its tier). The
   invite code is the gate, so `REQUIRE_TICKET_TO_REGISTER` is bypassed on this path.
4. Ensure `magic_access_token` (generate `secrets.token_urlsafe(32)` if missing).
5. Create the `User` (email + `get_password_hash(password)` + `attendee_id`); commit.
6. **Fire cold-start enrichment** detached: `asyncio.create_task(run_full_enrichment(attendee.id))`.
7. Return a `Token` (JWT) → frontend auto-logs them in, exactly like `register`.

No welcome email on join (they are already in the app). Optional later add.

### Background triggers — two functions, shared stages

New single-purpose module `app/services/profile_pipeline.py` (clean boundary; both
auth and matches routes import from it). Both functions run detached via
`asyncio.create_task` (the established pattern — `BackgroundTasks` would hold the
request worker through a 10-20s OpenAI/Grid pipeline and 504 the edge). Each stage
is wrapped in its own try/except so one failure cannot block the rest; failures are
logged, the account/profile stays usable, and the nightly cron backfills.

```python
async def refresh_profile_matches(attendee_id: UUID) -> None:
    """LIGHT path: re-embed from current profile + regenerate matches.
    Used by every profile save (Profile page, magic-link, Concierge) and as
    stages 2-3 of the cold-start join. No re-scraping."""
    async with async_session() as db:
        engine = MatchingEngine(db)
        attendee = await db.get(Attendee, attendee_id)
        if not attendee:
            return
        await engine.process_attendee(attendee)          # AI summary + intents + ICP + embedding
        await engine.generate_matches_for_attendee(
            attendee_id, clear_existing=True, notify=False
        )

async def run_full_enrichment(attendee_id: UUID) -> None:
    """COLD-START path: Grid + website enrichment, THEN refresh_profile_matches.
    Used by the sponsor join (no enrichment data yet) and by an escalated save."""
    async with async_session() as db:
        attendee = await db.get(Attendee, attendee_id)
        if not attendee:
            return
        try:
            svc = EnrichmentService()
            attendee.enriched_profile = await svc.enrich_attendee(attendee)  # Grid + website (+ Voyager fallback)
            await db.commit()
        except Exception:
            logger.exception("full-enrichment: enrich stage failed for %s", attendee_id)
    await refresh_profile_matches(attendee_id)  # fresh session inside
```

Notes:
- `enrich_attendee` returns a NEW dict, so we assign it to `enriched_profile`
  (mutate-and-reassign-same-ref is a silent no-op for JSONB).
- Enrich runs **before** `process_attendee` so the embedding includes Grid data.
- `notify=False` — a brand-new joiner has no mutual matches to notify about, and we
  do not want a save to spam emails.
- `process_attendee` already emits a factual stub for sparse profiles
  (anti-hallucination), so no fabrication on thin joins.

The existing `_process_attendee_bg` in auth.py (light AI pass, embed-only, **no
match generation**) is replaced by `refresh_profile_matches`. This is a deliberate
behaviour change to `register`: new ticket-holder registrations will now generate
matches immediately instead of waiting for the nightly cron — consistent with the
"save triggers matches for everyone" philosophy. The Concierge save path is
refactored to call `refresh_profile_matches` too, so all entry points share one
function.

### Wiring the universal save-trigger

| Save surface | File | Change |
|---|---|---|
| Profile page | `PUT /auth/profile` (auth.py:240) | After commit, `asyncio.create_task(refresh_profile_matches(attendee.id))`. Keep the `embedding = None` clear (harmless; `process_attendee` regenerates it). |
| Magic-link | `PATCH /matches/m/{token}/profile` (matches.py:372) | Same detached call after commit. |
| AI Concierge | `POST /chat/...save-field` | Refactor its existing BackgroundTasks re-embed+rematch to call `refresh_profile_matches` (behaviour-preserving consolidation). |
| Registration | `POST /auth/register` | Replace `_process_attendee_bg` with `refresh_profile_matches` — registrants now get matches immediately (was embed-only, cron-deferred). |
| Sponsor join | `POST /auth/join` | `run_full_enrichment` (cold start). |

**Optional escalation (recommended, small):** in `PUT /auth/profile`, if the save
changes `company`, `company_website`, or sets `linkedin_url` for the first time and
that source is not yet enriched, dispatch `run_full_enrichment` instead of
`refresh_profile_matches` so the new company gets a Grid/website pass. Otherwise the
light path is correct and avoids redundant scraping.

### Frontend

- New route in `App.tsx`: `<Route path="/join/:code" element={<SponsorJoin />} />`.
- New page `frontend/src/pages/SponsorJoin.tsx`: sponsor-branded heading, reads
  `:code` from the URL (never hardcoded — so the code is not baked into the JS
  bundle), posts it with the form via a new `joinViaInvite(payload)` in
  `api/client.ts`. On success, store the JWT through `AuthContext` (same as
  `register`) and navigate to `/matches`.
- Fields: name, email, password, company, title, LinkedIn URL,
  "Who do you want to meet?" (`target_companies`), goals, interests, privacy toggle.
  Enough for good enrichment without a wall of inputs; mirrors `Register.tsx`
  validation (client-side password rule + `https://` LinkedIn normalisation).
- States: invalid/expired code → friendly full-page message; email already has a
  login → inline error linking to `/login`; success → brief "Setting up your
  matches…" then redirect.

## How "enrich → unlock more matches" works (reference)

Two independent effects, documented so future work does not conflate them:

1. **How many you see (cap 5 → 10 → 20):** computed live at read time from
   `profile_data_quality(attendee)` on every matches fetch (matches.py:172). Unlock
   is instant — the deep pool of ~20 candidates already exists; the tier only caps
   display. No background job needed.
2. **Which ones you get (quality):** depends on the embedding, built from the
   profile. New info → embedding must regenerate → pgvector re-retrieve → GPT
   re-rank. This is what `refresh_profile_matches` does on save. Previously this
   lagged to the nightly cron for Profile-page saves; the universal trigger closes it.

LinkedIn/Grid are not what unlock tiers — the user's own typed fields are. They add
raw material to the embedding.

## Security & abuse

- Constant-time invite-code compare; the code lives only in env + the shared link,
  read from the URL at runtime, never hardcoded in the bundle.
- `ticket_type` forced to SPONSOR server-side — clients cannot self-promote.
- `EmailStr` + password-strength validation; endpoint rate-limited 5/min per IP.
- **Honest trade-off:** a single shared link is inherently shareable, so public
  leakage → junk SPONSOR accounts is possible. Mitigations if it happens: rotate the
  env code (kills the old link) or graduate to Approach B (per-link expiry/usage
  caps). Accepted for now per "anyone with access can use it."
- Junk rows would be SPONSOR-tagged, so they are filterable/auditable if cleanup is
  ever needed.

## Edge cases

- Invite code unset → 403 / disabled page (feature off by default).
- Email already a `User` → 400 "log in instead."
- Email already an attendee (pre-loaded sponsor, or bought a ticket) → merge onto
  that row, tag SPONSOR, attach the login (same merge as `register`).
- Grid/OpenAI failure during enrichment → caught per-stage, logged; account still
  works; nightly cron backfills.
- Sparse profile → factual stub from `process_attendee`, no hallucination.
- Repeated saves → only the saver's own ~8 GPT rerank calls run; cost bounded; the
  light path skips re-scraping.

## Testing (TDD)

Backend (pytest, async client):
- valid code → creates `User` + `Attendee` tagged SPONSOR, returns a token.
- wrong code → 403; unset code → 403.
- existing-User email → 400.
- existing-attendee email → merge + login attached, tier becomes SPONSOR.
- `JoinRequest` validation (password rules, blank name, bad email).
- `run_full_enrichment` dispatches enrich → process_attendee → generate_matches
  (services mocked); a failure in the enrich stage still reaches
  `refresh_profile_matches`.
- `PUT /auth/profile` and `PATCH /m/{token}/profile` dispatch
  `refresh_profile_matches` (mocked) after a successful save.

Frontend:
- `tsc -b && vite build` clean.
- Browser smoke: open `/join/<code>` → fill form → submit → land on `/matches`;
  open `/join/<wrong>` → see invalid-link state.

## Files touched

- `backend/app/core/config.py` — `SPONSOR_INVITE_CODE`.
- `backend/app/schemas/auth.py` — `JoinRequest`.
- `backend/app/api/routes/auth.py` — `POST /auth/join`, `_upsert_attendee_from_payload`
  helper, save-trigger on `PUT /auth/profile`, swap `register`'s `_process_attendee_bg`
  for `refresh_profile_matches`.
- `backend/app/api/routes/matches.py` — save-trigger on `PATCH /m/{token}/profile`.
- `backend/app/services/profile_pipeline.py` — new: `refresh_profile_matches`,
  `run_full_enrichment`.
- `backend/app/api/routes/chat.py` — Concierge save refactored onto
  `refresh_profile_matches`.
- `backend/.env.example` — `SPONSOR_INVITE_CODE=`.
- `frontend/src/App.tsx` — `/join/:code` route.
- `frontend/src/pages/SponsorJoin.tsx` — new page.
- `frontend/src/api/client.ts` — `joinViaInvite`.
- `CLAUDE.md`, `session_log.md`, `whats_next.md`, `project_state.md` — docs.

## Rollout

1. Ship code (off by default — blank `SPONSOR_INVITE_CODE`).
2. Smoke-test on a deploy with a temporary code; verify a real join → enrichment →
   matches end-to-end.
3. Set the production `SPONSOR_INVITE_CODE` in Railway; share
   `https://meet.proofoftalk.io/join/<code>` with sponsors.
4. Operator runs the next LinkedIn scrape pass to pick up joiners with linkedin_url.
