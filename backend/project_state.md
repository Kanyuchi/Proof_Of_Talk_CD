# Project State — backend

## What's Working
- Extasy → RDS pipeline pulls PAID + REDEEMED orders (complimentary tickets included)
- 38 attendees in RDS, ~129 matches, enrichment coverage ~100%
- Green EC2 (3.239.218.239) serving production via meet.proofoftalk.io
- OpenAI API key working on EC2 (enrichment, embeddings, match generation all functional)
- Supabase tables created (`attendees`, `matches`, `users`) with indexes + triggers
- 24 Extasy attendees synced to Supabase

## Broken / Incomplete
- Supabase only has Extasy attendees (24) — seed profiles, matches, embeddings not yet migrated
- Frontend may still need config update to read from Supabase instead of RDS

## Key Decisions Made
- Include REDEEMED status alongside PAID for Extasy ingestion (Jessica confirmed all valid orders)
- Exclude FAILED and REFUNDED statuses
- Direct Postgres connection to Supabase (SUPABASE_DB_URL in .env) for automation

## Current Focus
- Verify frontend works with Supabase data, confirm order count with Chiara
