# Adoption & Usage Tracking — Design

**Date:** 2026-05-24
**Status:** Approved (design), pending implementation plan
**Author:** Claude (with Shaun)

## Problem

Zohair needs to see whether attendees are actually *using* the matchmaker —
"who has logged in or created an account." Today we can answer almost none of it:

- **Accounts** exist in the `users` table with a `created_at`, but no dashboard
  surfaces the count. (A one-off query on 2026-05-24 showed **162 accounts**, 154
  real, with a clear spike of **144 in 3 days** tracking the 05-21→23 welcome-email
  waves — strong directional adoption signal.)
- **Logins are not recorded at all** — there is no `last_login` column and no
  events table. "Who logged in / when / how often" is historically unanswerable.
- **Magic-link usage is invisible.** The *primary* access path is the welcome
  email's "Open your matches" button → `GET /matches/m/{token}`, which needs **no
  account**. Most real usage produces zero `users` rows, so account count is a
  *floor* on engagement, not the real figure.

The app launched ~2026-05-21 (first welcome waves). Any usage metric must be
**anchored to a "tracking start" date and grow forward** — fixed 30-day (and, in
week one, 7-day) rolling windows would imply pre-launch history we don't have.

## Goals

1. Surface **accounts created** + the **signup trend** (we already have this data
   from `users.created_at`).
2. Start recording **real usage** — both password logins *and* magic-link opens —
   so engagement becomes answerable **from tracking-start forward**.
3. Show a **day-by-day usage trend from launch forward** (not just a live number).
4. Present it honestly: usage metrics labeled with the tracking-start date so the
   first days' necessarily-low numbers aren't misread as low engagement.

## Non-Goals (YAGNI)

- **No per-request events table.** Unbounded growth + retention concerns; not
  needed for a pre-event audience. (Noted as a future upgrade if true DAU/MAU
  trend granularity is ever wanted.)
- No backfill of historical usage — impossible; we never recorded it.
- No per-attendee "last seen" surfaced in the attendee-facing UI (organiser
  dashboard only). Privacy: usage timestamps are admin-only.
- No real-time analytics, funnels, or cohort analysis.

## Approach

**Approach A — timestamp columns** (chosen over an events table). Two nullable
columns capture "most recent activity"; a tiny daily snapshot table captures the
"per-day" history that overwriting timestamps would otherwise lose.

### Data model

Alembic migration adds:

- `users.last_login_at TIMESTAMP NULL` — set on successful password login.
- `attendees.last_seen_at TIMESTAMP NULL` — set on magic-link match view.

New table `usage_daily` (one row per day):

| column | type | meaning |
|---|---|---|
| `day` | DATE PRIMARY KEY | snapshot date (UTC) |
| `total_accounts` | INT | `COUNT(users)` at snapshot time |
| `real_accounts` | INT | accounts excl. admin + `@demo.proofoftalk.io` |
| `active_today` | INT | distinct people with `last_active` within the prior 24h |
| `cumulative_active` | INT | distinct people ever active since tracking began (non-null `last_active`) |

"**last_active**" for a person = `max(users.last_login_at, attendees.last_seen_at)`
for their linked rows. Magic-link-only users (no account) are counted via
`attendees.last_seen_at`.

### Write hooks (throttled)

Both hooks **only UPDATE if the existing value is NULL or older than ~1 hour**, so
a page refresh or repeated magic-link opens don't write on every request.

- `POST /auth/login` (auth.py:267), on successful auth → `user.last_login_at`.
- `GET /matches/m/{token}` (matches.py:154), on valid token → `attendee.last_seen_at`.
  This is the hook that captures the magic-link majority.

The write is best-effort and must never break the response (wrap in try/except;
the magic-link view rendering takes priority over recording the timestamp).

### Daily snapshot cron

A new scheduler job (alongside the existing 02:00–03:00 UTC crons in
`app/main.py`) runs once daily, computes the `usage_daily` row for that day, and
upserts it (idempotent on `day`). Writes a `sync_status` heartbeat like the other
crons so a silent failure is visible. ~1 row/day.

### Dashboard endpoint

New `GET /dashboard/adoption` (admin-gated, mirrors existing dashboard routes).
Returns:

```jsonc
{
  "tracking_started_at": "2026-05-24",        // min(day) in usage_daily, or deploy date
  "accounts": {
    "total": 162, "real": 154,                 // real = excl admin + demo
    "linked_to_attendee": 161,
    "pct_of_directory": 17.7,                   // real / directory size
    "directory_size": 912
  },
  "signups_by_day": [{ "day": "2026-05-21", "n": 46 }, ...],  // from users.created_at (historical)
  "usage": {
    "cumulative_active": 0,                     // distinct ever-active since tracking
    "active_last_7d": 0,                        // rolling; in week 1 ≈ since-launch
    "magic_link_active": 0,                     // distinct attendees with last_seen_at
    "login_active": 0                           // distinct users with last_login_at
  },
  "usage_by_day": [{ "day": "...", "active_today": 0, "cumulative_active": 0 }, ...]  // from usage_daily
}
```

`signups_by_day` is available immediately (historical). `usage.*` and
`usage_by_day` start at zero and fill in from tracking-start forward.

### Frontend

One **"Adoption & Usage"** card on the organiser Dashboard, styled to match the
existing Sync Health / Ticket Types panels:

- Top line: accounts total / real / % of directory claimed.
- Signup sparkline/bars (shows the welcome-email spike).
- Usage block: cumulative-active + active-last-7d, each tagged
  *"since tracking began 2026-05-24"*.
- Day-by-day usage trend (small line/bar chart) once `usage_daily` has rows.
- An empty/explainer state for the usage block before data accumulates
  ("Usage tracking started 2026-05-24 — numbers build from here").

## Error handling

- Write hooks are best-effort, wrapped so they never affect the user response.
- Throttle avoids write amplification on refresh/repeat opens.
- Daily cron is idempotent (upsert on `day`) and heartbeats to `sync_status`.
- Endpoint degrades gracefully: if `usage_daily` is empty, return live counts +
  empty `usage_by_day`.

## Testing

- **Migration**: columns + table exist, nullable, defaults sane.
- **Write-hook unit tests**: login sets `last_login_at`; second login within 1h
  does NOT rewrite (throttle); magic-link open sets `last_seen_at` (throttled);
  hook failure does not break the login/magic-link response.
- **Snapshot job test**: with seeded timestamps, `usage_daily` row has correct
  `active_today` / `cumulative_active`; re-run same day is idempotent.
- **Endpoint test**: admin-only (401/403 for non-admin); shape matches; real-vs-
  demo exclusion correct; `pct_of_directory` math.
- **Frontend**: panel renders with data; empty usage state pre-accumulation.

## Rollout

1. Ship migration + write hooks + endpoint + panel together.
2. On deploy day, `tracking_started_at` = that date; usage numbers begin at 0 and
   grow. Signup/account numbers are correct immediately (historical).
3. Daily cron starts populating `usage_daily` from day one.

## Future (deferred)

- Per-request `access_events` table if true DAU/MAU granularity / funnels are
  ever needed.
- Surfacing "last active" per attendee in the admin attendee list.
- Email-engagement (open/click) correlation if Resend webhooks are wired.
