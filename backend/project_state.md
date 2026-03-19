# Project State — backend

## What's Working
- Extasy → RDS pipeline pulls PAID + REDEEMED orders (complimentary tickets included)
- 38 attendees in RDS, 129 matches, 100% enrichment coverage
- Green EC2 (3.239.218.239) serving production via meet.proofoftalk.io
- OpenAI API key working on EC2
- **Supabase is a full mirror of RDS**: 38 attendees, 129 matches, all AI summaries + embeddings synced
- Direct Postgres connection to Supabase available (`SUPABASE_DB_URL` in .env)

## Broken / Incomplete
- Frontend may still need config update to read from Supabase instead of EC2/RDS
- Need to confirm order count with Chiara (Runa) — we have 24 from Extasy API

## Key Decisions Made
- Include REDEEMED status alongside PAID for Extasy ingestion (Jessica confirmed)
- Exclude FAILED and REFUNDED statuses
- Supabase is the final production database (full mirror of RDS)

## Current Focus
- Verify frontend works with Supabase data
- Confirm attendee count with Chiara
