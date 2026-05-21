# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. [launch] Continue welcome waves — 162 sent / 561 eligible remaining (~100/day from warm team@xventures.de via `send_welcome_batch.py --limit 100 --confirm`)
2. [auth] Pre-launch: fix `GET /api/v1/matches/pending-count` returning 422 for live users (missing/!required query param — seen in prod logs 2026-05-21)
3. [auth] EMAIL_MODE=all is now a pure LAUNCH decision (self-recovery already solved surgically via forced forgot-password). Before flipping, neutralise the `generate_all_matches` 739-blast footgun (it emails every attendee's top match).
4. Confirm attendee count with Chiara (email drafted — 24 valid from Extasy API)
3. Verify frontend at meet.proofoftalk.io shows vertical_tags in attendee profiles
4. Re-generate matches using vertical_tags as a matching signal (improve match quality)

## Soon
- Automate daily Extasy → RDS → Supabase sync
- Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Later / Backlog
- Retire RDS once Supabase confirmed as sole production DB
- Supabase Edge Functions for real-time match notifications

## Done ✓
- [auth] forgot-password self-recovery DEPLOYED (commit 3c303de, Railway c8a80f7c) — unclaimed attendees get a force-sent magic-link claim email; EMAIL_MODE stays allowlist so bulk triggers remain gated (2026-05-21)
- [launch] Welcome wave 2 sent: 100/100, 0 failed; Mauricio Magaldi Suguihura included (2026-05-21)
- [auth] forgot-password no longer dead-ends the 700 unclaimed attendees — falls back to magic-link claim email; resent Tommi Vuorenmaa's welcome (2026-05-21)
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
- Created Supabase tables (attendees, matches, users) (2026-03-19)
- Full RDS → Supabase sync: 38 attendees, 129 matches, all enrichment data (2026-03-19)
- Added vertical_tags — 11 1000minds sector verticals, 38/38 attendees classified (2026-03-19)
