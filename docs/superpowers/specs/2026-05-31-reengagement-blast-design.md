# Re-engagement blast to unregistered ticket holders - design

**Date:** 2026-05-31
**Trigger:** Adoption is 438/1,640 (26.2%) at T-minus-2. 1,202 attendees have a magic token but no `users` row. Goal: convert as many as possible before doors open Jun 2.

## Diagnosis (real numbers)

From Resend list API + prod Supabase, 2026-05-31:

| Metric | Value | Source |
|---|---|---|
| Total attendees | 1,640 | `attendees` |
| `has_account=true` (logged in at least once) | 438 | `LEFT JOIN users` |
| `has_account=false` (no `users` row) | 1,202 | same |
| **Targetable** (token + not opted out + not gated + not demo + not placeholder) | **1,042** | filters below |
| Of those: 0 total matches | 5 | skip |
| Of those: 8+ total matches | 908 (87%) | strong personal value prop |
| Of those: someone already wants to meet them | 198 (~19%) | reciprocity hook applies |
| Welcome emails sent (Resend, since 2026-05-18) | 1,696 | Resend list API |
| Welcome delivery rate | 96.5% (1,637 delivered, 58 bounced) | Resend `last_event` |
| Welcome open / click rate | **unknown** | tracking is OFF in `email.py` |

Implication: deliverability is healthy. We don't know whether recipients open or act, because Resend open/click tracking is disabled in our send code. We'll enable it on this template only.

## Approach

A single targeted blast TODAY to the 1,042 targetable, plus the existing T-1 reminder firing tomorrow 17:00 Paris as the natural second touch.

The T-1 reminder code already targets the same cohort (filtered to those with at least 1 curated match: ~1,000 of the 1,042) with personalised top-3 match cards and "Tomorrow at the Louvre, {first_name}" urgency. It does not need code changes. Two touches, two distinct hooks: today's blast uses reciprocity + concrete match count; T-1 uses time urgency.

### Why not modify T-1 itself

Originally considered. Rejected because:
1. T-1 is date-locked via `CronTrigger(year=2026, month=6, day=1)` and fires once at 17:00 Paris tomorrow. Touching it 24h before fire is risk-asymmetric.
2. Its CTA already deep-links to `/m/{token}`, which renders the Phase 1-4 funnel (claim panel default-expanded, reciprocity reveal, paywall) for `has_account=false` recipients. The conversion path is already optimised at the landing, not the email.
3. A second touch with a distinct angle outperforms a single "improved" touch in B2B re-engagement (proven pattern: LinkedIn, Notion).

## Cohort (SQL)

```sql
SELECT a.*
FROM attendees a
LEFT JOIN users u ON u.attendee_id = a.id
WHERE u.id IS NULL                            -- has_account = false
  AND a.email_opt_out IS NOT TRUE             -- respect prior unsubscribe
  AND a.matching_consent != 'pending'         -- skip gated speakers
  AND a.magic_access_token IS NOT NULL        -- need a valid magic link
  AND a.email NOT LIKE '%@demo.proofoftalk.io'
  AND a.email NOT LIKE '%@speaker.proofoftalk.io'
```

Send count target: **1,042**. Drop the 5 with zero matches at runtime (no honest value prop).

Send cap: one wave today. Precedent from welcome rollout (411 on 05-21, 405 on 05-22, no deliverability drop on warm `team@xventures.de`).

## Subject lines (personalised per recipient)

| Recipient state | Subject | Rationale |
|---|---|---|
| Has ≥1 incoming interest (~198) | `{M} people want to meet you at Proof of Talk` | Strongest hook: reciprocity + specific number |
| Has ≥1 curated match, 0 incoming (~840) | `Your {N} matches at the Louvre, this Tuesday` | Concrete personal count + venue + day-of-week anchor |
| Has 0 matches (5) | (skip) | No honest hook |

Preview text (all variants): `You haven't claimed your account yet. We've matched you with people you'll want to meet.`

## Email body

Same Louvre-banner shell as the existing welcome (via `_render_email`), new content:

1. `Hi {first_name},`
2. `You bought a Proof of Talk ticket but haven't opened your matchmaking yet.`
3. `We've matched you with {N} attendees.` + (if M > 0) `{M} of them have already said they want to meet you.`
4. **Top 2 match teaser cards**: name, title, company, one-line explanation. Reuse `_build_top_matches()` from `t_minus_one_reminder.py` (cap 2 instead of 3 to keep above-the-fold).
5. `The Louvre Palace. Tuesday and Wednesday. That's in 2 days.`
6. Primary CTA orange button: `See who wants to meet you` linking to `https://meet.proofoftalk.io/m/{token}` (Phase 1-4 funnel auto-expands the claim panel for `has_account=false`).
7. Soft footer line: `Can't make it? Opt out below.` + standard Unsubscribe + Preferences links.

No PWA install prompt. No secondary CTA. Reward-framed primary CTA, not task-framed ("set your password" was wrong on the welcome).

## Tracking

Enable Resend open + click tracking **on this template only** by passing tracking flags in the Resend payload from a new `send_reengagement_email()` function, not the shared `_send_email()`. Existing transactional sends stay un-tracked to keep change surface minimal.

Resend API: per-send `tracking` object documented at https://resend.com/docs/api-reference/emails/send-email#body-parameters (or equivalent header). Verify at implementation time.

Measured outcomes from Resend after send:
- `last_event = "opened"` → open count
- `last_event = "clicked"` → click count
- `last_event = "delivered"` (no further) → delivered-but-ignored

## Send mechanics

New script: `backend/scripts/send_reengagement_blast.py`. Clone of `send_welcome_batch.py` shape.

- Default: preview-only (prints recipient list + first 3 full rendered emails to stdout)
- `--confirm` to send
- `--limit N` to wave-cap
- `--only <email>` for single-recipient smoke
- `--status` to print ledger stats
- Ledger: `backend/exports/reengagement_sent.log` (separate from welcome ledger; same `email\tISO8601` format)
- Idempotent: skip anyone already in the ledger
- Cohort query exactly the SQL above

Send flow:
1. `--only shaun@proofoftalk.io --confirm` (visual + link smoke)
2. `--limit 50 --confirm` (deliverability smoke)
3. Full `--confirm` for remaining ~990
4. Wait ~2h, pull Resend open/click data

Kill switch: bail if `>5%` of first 100 sends return Resend non-200.

## Success criteria

Measured 24h post-send:
- Open rate ≥ 40% of delivered (B2B re-engagement industry benchmark 30-45%)
- Click rate ≥ 12% of delivered (industry benchmark 8-15%)
- 24h registration conversion ≥ 5% of delivered (= 50+ new accounts from this blast alone)

Combined with T-1: aim for **100+ new registrations** between today and event start.

## Out of scope (deferred)

- Changes to `t_minus_one_reminder.py` (intentionally untouched, see "Why not modify T-1")
- Changes to the welcome email template itself (replacement, not a fix on the existing template, is the v2 follow-up if this works)
- Threads engagement work (separate brainstorm; engagement asymmetry there is a content/cold-start problem, not a feature problem)
- A like button or notifications on Threads (premature until threads have content density)
- Enabling Resend tracking globally for all transactional sends (separate decision; mild CAN-SPAM consideration)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Deliverability drop on warm `team@xventures.de` | Single batch with bail-out at >5% non-200 in first 100 |
| Double-email annoyance vs T-1 | 24h gap + distinct angles (reciprocity today / urgency tomorrow) |
| `/m/{token}` landing breaks | Already in prod for weeks; Phase 1-4 funnel verified |
| Tracking pixel triggers spam filters | Resend's pixel is reputable; only enable on this one template |
| Recipient already on the welcome ledger from a stale send | Ledger checked at send time; separate `reengagement_sent.log` keeps the two batches independent |

## Timeline (today, 2026-05-31)

- Spec written + reviewed (this doc)
- Implementation plan via writing-plans skill
- Implement send script + tracking-enabled send function
- Single-recipient smoke (shaun@)
- 50-recipient deliverability smoke
- Full ~990 blast
- 2026-06-01 17:00 Paris: T-1 fires (existing cron, no change)
- 2026-06-01 evening: pull combined open/click/registration data
