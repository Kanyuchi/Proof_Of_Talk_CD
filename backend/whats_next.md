# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. Verify frontend at meet.proofoftalk.io pulls attendees from Supabase
2. Send email to Chiara to confirm Runa order count (24 valid vs her records)
3. Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Soon
- Automate daily Extasy sync via APScheduler cron
- pg_dump from RDS → Supabase (to include seed profiles, matches, embeddings)

## Later / Backlog
- Supabase Edge Functions for real-time match notifications

## Done ✓
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
- Created Supabase tables via direct Postgres connection (2026-03-19)
- Synced 24 Extasy attendees to Supabase (2026-03-19)
