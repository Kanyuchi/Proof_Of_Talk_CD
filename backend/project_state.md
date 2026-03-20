# Project State — backend

## What's Working
- Extasy → RDS pipeline pulls PAID + REDEEMED orders (complimentary tickets included)
- 38 attendees in RDS + Supabase, 129 matches, 100% enrichment coverage
- All 38 attendees have `vertical_tags` (1000minds sectors) + `intent_tags` (intents)
- Green EC2 (3.239.218.239) serving production via meet.proofoftalk.io
- OpenAI API key working on EC2
- Supabase is a full mirror of RDS with vertical_tags synced

## Broken / Incomplete
- Frontend doesn't yet display vertical_tags (needs UI update)
- Matching pipeline doesn't yet use vertical_tags as a signal
- 2 of 11 verticals unrepresented (bitcoin, prediction_markets) — no matching attendees yet

## Key Decisions Made
- Include REDEEMED status alongside PAID for Extasy ingestion (Jessica confirmed)
- vertical_tags (sector) is a separate dimension from intent_tags (what they want to do)
- 11 verticals aligned with 1000minds taxonomy

## Current Focus
- Confirm attendee count with Chiara, integrate vertical_tags into matching
