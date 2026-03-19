# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. Create `attendees` table in Supabase (run `scripts/supabase_setup.sql` in SQL editor)
2. Re-run `ingest_extasy.py` to sync all 38 attendees to Supabase
3. Verify frontend at meet.proofoftalk.io pulls updated attendee list from Supabase

## Soon
- Automate daily Extasy sync via APScheduler cron
- Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Later / Backlog
- pg_dump from RDS → Supabase (includes all embeddings + matches, avoids re-running enrichment)

## Done ✓
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
