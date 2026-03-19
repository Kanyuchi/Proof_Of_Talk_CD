# Project State — backend

## What's Working
- Extasy → RDS pipeline pulls PAID + REDEEMED orders (complimentary tickets included)
- 38 attendees in RDS, 129 matches (121 + 8 new for Pierre), enrichment coverage back to ~100%
- Green EC2 (3.239.218.239) serving production via meet.proofoftalk.io
- OpenAI API key working on EC2 (enrichment, embeddings, match generation all functional)

## Broken / Incomplete
- Supabase `attendees` table doesn't exist — `ingest_extasy.py` fails with 404
- Need to run `scripts/supabase_setup.sql` in Supabase SQL editor to create tables

## Key Decisions Made
- Include REDEEMED status alongside PAID for Extasy ingestion (Jessica confirmed all valid orders)
- Exclude FAILED and REFUNDED statuses

## Current Focus
- Supabase migration: create tables + sync data so frontend can pull from Supabase
