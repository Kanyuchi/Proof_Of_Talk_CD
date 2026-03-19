# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. Verify frontend at meet.proofoftalk.io pulls from Supabase correctly
2. Send email to Chiara to confirm Runa order count (24 valid vs her records)
3. Switch frontend/backend to use Supabase as primary DB (if not already)

## Soon
- Automate daily Extasy → Supabase sync
- Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Later / Backlog
- Supabase Edge Functions for real-time match notifications
- Retire RDS once Supabase is confirmed as sole production DB

## Done ✓
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
- Created Supabase tables (attendees, matches, users) (2026-03-19)
- Full RDS → Supabase sync: 38 attendees, 129 matches, all enrichment data (2026-03-19)
