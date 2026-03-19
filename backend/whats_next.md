# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. Create `attendees` table in Supabase so `ingest_extasy.py` can sync
2. Run enrichment + match generation for Pierre Kaklamanos (new comp ticket attendee)
3. Top up OpenAI credits / replace API key on EC2 (429 blocker for enrichment)
4. Deploy updated code to green EC2 (extasy_sync.py changes)

## Soon
- Re-run full Supabase ingest once table exists
- Verify frontend pulls updated attendee list

## Later / Backlog
- Automate daily Extasy sync via APScheduler cron

## Done ✓
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
