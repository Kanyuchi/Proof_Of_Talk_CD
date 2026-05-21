# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. [auth] Deploy the forgot-password magic-link fallback to Railway (committed 324e8a9, gated/safe) + decide EMAIL_MODE=all flip — until flipped, the 700 unclaimed can't self-recover and ops must resend welcomes manually
2. Confirm attendee count with Chiara (email drafted — 24 valid from Extasy API)
3. Verify frontend at meet.proofoftalk.io shows vertical_tags in attendee profiles
4. Re-generate matches using vertical_tags as a matching signal (improve match quality)

## Soon
- Automate daily Extasy → RDS → Supabase sync
- Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Later / Backlog
- Retire RDS once Supabase confirmed as sole production DB
- Supabase Edge Functions for real-time match notifications

## Done ✓
- [auth] forgot-password no longer dead-ends the 700 unclaimed attendees — falls back to magic-link claim email; resent Tommi Vuorenmaa's welcome (2026-05-21)
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
- Created Supabase tables (attendees, matches, users) (2026-03-19)
- Full RDS → Supabase sync: 38 attendees, 129 matches, all enrichment data (2026-03-19)
- Added vertical_tags — 11 1000minds sector verticals, 38/38 attendees classified (2026-03-19)
