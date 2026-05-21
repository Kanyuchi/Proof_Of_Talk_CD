# Project State — backend

## What's Working
- [matches] `GET /api/v1/matches/pending-count` resolves correctly (was 422 — shadowed by the `/{attendee_id}` UUID route; fixed + verified on prod 2026-05-21, commit fbfd954). Rule: static GET paths must be declared above `/{attendee_id}` in matches router.
- [auth] Login requires claiming a pre-loaded attendee via the welcome email's magic link (`/m/{token}?unlock=1` → set password). forgot-password now force-sends that claim email for unclaimed attendees (DEPLOYED 2026-05-21, Railway c8a80f7c) — self-service recovery works WITHOUT flipping EMAIL_MODE. As of 2026-05-21: ~40/739 claimed; 261 welcome emails sent (462 remaining). EMAIL_MODE stays `allowlist`; flipping to `all` is now an unblocked launch decision — the `generate_all_matches` blast footgun is guarded (notify=False on bulk rebuild, commit 85b41d3).
- Extasy → RDS pipeline pulls PAID + REDEEMED orders (complimentary tickets included)
- 38 attendees in RDS + Supabase, 129 matches, 100% enrichment coverage
- All 38 attendees have `vertical_tags` (1000minds sectors) + `intent_tags` (intents)
- Green EC2 (3.239.218.239) serving production via meet.proofoftalk.io
- OpenAI API key working on EC2
- Supabase is a full mirror of RDS with vertical_tags synced

## Broken / Incomplete
- Frontend doesn't yet display vertical_tags (needs UI update)
- Matching pipeline doesn't yet use vertical_tags as a signal
- 2 of 11 verticals unrepresented (bitcoin, prediction_markets) — no matching attendees yet

## Key Decisions Made
- Include REDEEMED status alongside PAID for Extasy ingestion (Jessica confirmed)
- vertical_tags (sector) is a separate dimension from intent_tags (what they want to do)
- 11 verticals aligned with 1000minds taxonomy

## Current Focus
- Confirm attendee count with Chiara, integrate vertical_tags into matching
