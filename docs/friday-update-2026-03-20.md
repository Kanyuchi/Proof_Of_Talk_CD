Subject: POT Matchmaker — Weekly Update (March 20)

Hey everyone,

Sending you my weekly overview below:

**Key results:**
- Production live at `https://meet.proofoftalk.io`
- Supabase database fully synced (38 attendees, 129 matches, all AI data)
- 1000minds sector verticals implemented — 38/38 attendees auto-classified
- Complimentary/voucher tickets now included in pipeline (Jessica's request)

**Progress on last week's priorities:**
- Fix critical issues from testing feedback — **done** (503 on Netlify resolved, trailing-slash redirect fix)
- Production decision: Blue or Green — **done** (Green confirmed)
- Production deployment to `meet.proofoftalk.io` — **done** (live on Netlify + green EC2 backend)
- Soft launch to first 50 attendees — **pending** (need more attendees in Extasy before launch wave)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## What shipped this week

- **Production domain**: `https://meet.proofoftalk.io` — Netlify frontend proxying `/api/*` to green EC2 (`3.239.218.239`)
- **Complimentary tickets**: added `REDEEMED` status alongside `PAID`; pipeline now pulls all valid Extasy orders (paid + comp/voucher)
- **Supabase fully synced**: tables created, 38 attendees + 129 matches + all AI data mirrored from RDS — ready for migration cutover
- **1000minds vertical_tags**: GPT-4o classifies every attendee into 11 sector verticals (e.g. `investment_and_capital_markets`, `infrastructure_and_scaling`, `tokenisation_of_finance`); all 38/38 classified
- **503 fix**: root cause was FastAPI trailing-slash redirect producing a `localhost` URL that Netlify couldn't follow; fixed by removing trailing slash from route definitions
- **OpenAI API key**: replaced on EC2, enrichment pipeline fully functional again (no more 429 errors)

## By the numbers

| Metric | Last Week | This Week | Change |
|--------|-----------|-----------|--------|
| Attendees | 34 | 38 | +4 |
| Matches | 121 | 129 | +8 |
| Enrichment coverage | 100% | 100% | — |
| Avg match score | 0.69 | 0.69 | — |
| Verticals classified | — | 38/38 | new |
| Supabase sync | Not started | Complete | new |

**Vertical distribution** (9 of 11 verticals represented):

| Vertical | Count |
|----------|-------|
| Investment & Capital Markets | 27 |
| Infrastructure & Scaling | 25 |
| Tokenisation of Finance | 13 |
| Ecosystem & Foundations | 12 |
| Decentralized Finance | 12 |
| AI, DePIN & Frontier Tech | 10 |
| Decentralized AI | 7 |
| Policy, Regulation & Macro | 5 |
| Culture, Media & Gaming | 1 |

## Feedback needed

1. Does the vertical classification look right? (can share per-attendee breakdown)
2. Chiara: can you confirm 24 valid orders in Runa/Extasy?
3. Should `vertical_tags` be visible to attendees in the UI, or organiser-only?
4. Priority call: integrate verticals into matching algorithm, or focus on attendee onboarding flow?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Focus for next week:**
- Confirm attendee count with Chiara (24 valid orders?)
- Integrate `vertical_tags` into matching pipeline (cross-vertical matches score higher)
- Display `vertical_tags` in frontend match cards
- Automate daily Extasy → Supabase sync
- Activate SES email (sender verification in AWS console)

**Wins Worth Celebrating:**
- `meet.proofoftalk.io` is LIVE
- Supabase migration complete (full data mirror)
- 1000minds vertical taxonomy implemented — 38/38 classified
- Complimentary tickets flowing through pipeline
- OpenAI API working on EC2

— Kanyuchi
