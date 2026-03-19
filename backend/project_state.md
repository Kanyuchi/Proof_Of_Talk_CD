# Project State — backend

## What's Working
- Extasy → RDS pipeline now pulls PAID + REDEEMED orders (complimentary tickets included)
- 38 attendees in RDS, 121 matches, 97% enrichment coverage
- Green EC2 (3.239.218.239) serving production via meet.proofoftalk.io

## Broken / Incomplete
- Supabase `attendees` table doesn't exist — `ingest_extasy.py` fails with 404
- EC2 OpenAI API key has hit quota limit — enrichment/embedding/match-gen fail with 429
- Pierre Kaklamanos not yet enriched (just loaded, enrichment skipped)

## Key Decisions Made
- Include REDEEMED status alongside PAID for Extasy ingestion (Jessica confirmed all valid orders, not just paid)
- Exclude FAILED and REFUNDED statuses

## Current Focus
- Getting complimentary ticket holders into the matchmaking pipeline
