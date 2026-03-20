# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. Confirm attendee count with Chiara (email drafted — 24 valid from Extasy API)
2. Verify frontend at meet.proofoftalk.io shows vertical_tags in attendee profiles
3. Re-generate matches using vertical_tags as a matching signal (improve match quality)

## Soon
- Automate daily Extasy → RDS → Supabase sync
- Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Later / Backlog
- Retire RDS once Supabase confirmed as sole production DB
- Supabase Edge Functions for real-time match notifications

## Done ✓
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
- Created Supabase tables (attendees, matches, users) (2026-03-19)
- Full RDS → Supabase sync: 38 attendees, 129 matches, all enrichment data (2026-03-19)
- Added vertical_tags — 11 1000minds sector verticals, 38/38 attendees classified (2026-03-19)
