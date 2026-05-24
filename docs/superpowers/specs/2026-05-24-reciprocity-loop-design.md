# Reciprocity Loop — Design

**Date:** 2026-05-24
**Status:** Approved (design); awaiting spec review before implementation plan
**Owner:** Shaun

## Problem

The matchmaker has 6,187 generated matches but only **6 mutual matches** and **1 booked
meeting**. The funnel leak, measured live on prod 2026-05-24:

| Stage | Count | % of directory |
|---|---|---|
| Real directory | 911 | 100% |
| Created an account | 161 | 18% |
| Took any action (accept/decline) | 39 people | 4.3% |
| One-sided accepts (dormant demand) | 135 | — |
| Mutual matches | 6 | — |
| Booked meetings | 1 | 0.1% |

Two structural causes, both confirmed in code:

1. **Nobody is pulled back to act on incoming interest.** The in-app "Requests" surface
   already exists (`MyMatches.tsx` Requests tab + `Layout.tsx` nav badge backed by
   `GET /matches/pending-count`), but there is **no email that fires on the *first* accept**.
   The only mutual-interest email fires on *mutual* (both already accepted) — too late — and
   even that is gated to team-only by `EMAIL_MODE=allowlist`.
2. **No-login users cannot accept back.** 82% of the directory has no account. The magic-link
   page (`MagicMatches.tsx`) supports view/profile/photo/defer/claim but **accept/decline is
   auth-only** (`PATCH /matches/{id}/status` requires `user.attendee_id`). So the targets of the
   135 one-sided accepts — mostly account-less — literally cannot close the mutual without first
   claiming an account (setting a password) at the moment of peak intent.

The event is **June 2–3, 2026 (9 days out)**. This is a sprint, not a retention curve: the goal
is to convert one-sided accepts → mutuals → booked meetings before the event, and to give each
attendee a *reason to return* (the pull-back email).

## Goal

Close the reciprocity loop: a no-login attendee receives "N people want to meet you", clicks the
magic link, lands on their Requests tab, and accepts back in **one tap** — creating a mutual match.

## Non-goals (v1)

- "New since last visit" delta (the Requests tab already shows incoming clearly).
- Tokenless slot scheduling — booking still nudges account-claim (hybrid decision).
- Flipping `EMAIL_MODE=all` (would also fire the deliberately-killed match-intro mass blast).
- No-login messaging.

## Decisions locked

| Decision | Choice | Why |
|---|---|---|
| Pull-back mechanism | Instant-feel via **near-real-time cron**, not request-path send | `email.py:58` forbids `force=True` from request paths (warm-domain guardrail); cron aggregates multiple accepts into one email and needs no `EMAIL_MODE` flip |
| Loop closure for no-login | **Tokenless accept-back** (`PATCH /m/{token}/status`); booking stays account-gated | Accepting is low-stakes and must be frictionless; scheduling/messaging can stay behind claim |
| v1 vs fast-follow | v1 = tokenless accept + **one-time backlog blast** + Requests UI on magic page + migration. Recurring cron **and** un-gating the mutual-completion email = **fast-follow** | Backlog blast to the 135 is the biggest lever and needs no cron; the cron only matters for new accepts that pile up days later (operator re-runs the script until it lands). Un-gating the mutual email correctly requires moving it off the request path (same `force` guardrail), so it rides with the cron |

## Components

### 1. Tokenless accept-back (backend)

New endpoint `PATCH /api/v1/matches/m/{token}/status`, mirroring the ownership-check pattern of
the existing `PATCH /m/{token}/defer` (`matches.py:232`).

- Body: `{ "status": "accepted" | "declined", "decline_reason": str | None }`.
- Resolve attendee by `magic_access_token`; 404 if the match doesn't belong to them.
- Set **only the caller's own side**: `status_a` if `attendee.id == match.attendee_a_id`, else
  `status_b`. Never let a token holder set the other party's side.
- Recompute overall via existing `_compute_overall_status(status_a, status_b)`.
- **Sends no email inline** — the request path stays `force`-clean. When the pair becomes mutual,
  the person who just accepted sees the mutual UI + book-a-slot chips immediately in-app; the
  other party's mutual-completion email is handled by the fast-follow notify path (§4), never from
  this request.
- Return `_build_match_response(...)` like the defer endpoint.

### 2. Tokenless accept-back (frontend)

`MagicMatches.tsx`:

- Add a **Requests** surface mirroring `MyMatches.tsx`'s logic
  (`isRequestToMe = other_status === "accepted" && viewer_status === "pending"`), rendering
  "N people want to meet you" with Accept / Decline buttons wired to the new token endpoint.
- Deep-link support: read `?tab=requests` and open that surface on load (the email CTA targets it).
- Apply the same deep-link to `MyMatches.tsx` so account-holders land correctly too.
- After accept → invalidate `["magic-matches", token]`; if it became mutual, show the existing
  mutual UI (book-a-slot chips already ship on the magic response via `mutual_free_slots`).

### 3. Pull-back notify ("N people want to meet you")

**One-time backlog catch-up (v1):** operator script `backend/scripts/notify_pending_interest.py`,
modeled on `send_welcome_batch.py`:

- Preview by default; `--confirm` to send; `--limit N` for waves; `--status` summary.
- Targets: attendees with ≥1 incoming-pending request
  (`other side accepted AND my side pending`) **and** `last_interest_notified_at IS NULL`,
  excluding `email_opt_out=true` and demo/staff.
- Per target: compute N = current incoming-pending count; send one "N people want to meet you"
  email (newsletter `_render_email` wrapper, warm `team@xventures.de`, magic-link CTA →
  `/m/{token}?tab=requests`); set `last_interest_notified_at = now`.
- Ledger file (e.g. `exports/interest_notified.log`) to prevent double-sends across runs.
- Respect the ~100/day warm-up cap; stage in waves.

**Recurring near-real-time cron (fast-follow, not v1):** every ~1–2h, find attendees whose
incoming-pending count rose since `last_interest_notified_at` and `> 24h` since last notify; send
the aggregated email; update the timestamp. Scheduled-job context, so `force=True` is legitimate.
Heartbeat row in `sync_status`. Until this lands, the operator re-runs the script daily.

### 4. Mutual completion email un-gated (fast-follow, not v1)

When a pair becomes mutual, both parties should receive the existing mutual-match email
("you matched, book a meeting") — today gated to team-only by `EMAIL_MODE=allowlist`. Un-gating it
correctly means **moving the send off the request path** onto the recurring cron (a scheduled
batch where `force=True` is legitimate), selecting pairs that became mutual since the last tick.
This rides with the cron in §3, not v1, because the existing request-path send cannot reach real
attendees without either violating the `force` guardrail or flipping `EMAIL_MODE=all`. Keep
`email_opt_out` enforcement and the unsubscribe token. In v1, the in-app mutual UI (book-a-slot
chips on the magic response) carries the experience for the person who just accepted.

### 5. Schema / throttle

- New column `attendees.last_interest_notified_at TIMESTAMP NULL` (Alembic migration).
- Single column is sufficient: the notify recomputes N at send time and the timestamp throttles
  re-notification. No per-side accept timestamps needed for v1.

## Email copy (v1)

- Subject: `{N} {people|person} want to meet you at Proof of Talk`
- Body: who they are (names/titles where available), one CTA button "See who wants to meet you"
  → `/m/{token}?tab=requests`. Newsletter wrapper, Louvre banners, terracotta CTA,
  Unsubscribe·Preferences. No em dashes.

## Deliverability

- All reciprocity mail from warm `team@xventures.de`.
- ≤100/day budget; backlog staged in waves.
- `email_opt_out` honored; per-target 24h throttle via `last_interest_notified_at`.
- No `force=True` from any request-triggered path (only operator script / scheduled cron).

## Testing (TDD)

- `PATCH /m/{token}/status`: invalid token (400/404), match-not-owned (404), sets correct side
  for party A vs B, declined sets reason, mutual computation when both accept, idempotency.
- Backlog script: dry-run selects the right cohort (excludes opt-out/demo/staff/already-notified),
  ledger prevents double-send, N computed correctly.
- Throttle: `last_interest_notified_at` set on send; not re-notified within 24h.
- Browser E2E: magic-link `?tab=requests` → Accept → becomes mutual → book-a-slot chip appears.

## Rollout

1. Migration `alembic upgrade head` against prod **before** merge (per playbook).
2. Merge backend + frontend; verify token endpoint live (401/200) + bundle grep for Requests UI.
3. Dry-run `notify_pending_interest.py`; review cohort; send first wave (≤100).
4. Watch Resend deliverability; watch mutual-match count climb on `/dashboard`.
5. Fast-follow: recurring cron.

## Success metric

Mutual matches climbing from 6, and booked meetings from 1, in the days after the backlog wave.
Read via the same prod queries used for this design (accepts / mutuals / bookings) plus the
adoption dashboard once `last_seen_at` accrues a few days of data.
