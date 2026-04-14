# Project State — POT Matchmaker

**Last updated:** 2026-04-14 (AI-inferred customer matching shipped — Z's ICP vision live, 247 matches @ 0.720 avg)
**Stack:** Python 3.12 / FastAPI / SQLAlchemy async · React 18 / TypeScript / Vite / Tailwind · **Supabase PostgreSQL** + pgvector · OpenAI (text-embedding-3-small + gpt-4o) · **Railway** (backend) · **Resend** (email) · Netlify (frontend)

---

## What's Working

- **3-stage AI matching pipeline** — Embed → pgvector retrieval → GPT-4o rank & explain; **247 matches** across 60 attendees, avg score **0.720**; vertical_tags + intent_tags + target_companies + inferred_customer_profile integrated into embeddings, GPT prompt, and deterministic reranking with COMPLEMENTARY_VERTICALS boost; ML feedback loop feeds decline reasons into GPT prompt
- **AI-inferred customer matching (Z's vision)** — each attendee gets a GPT-4o-inferred ICP stored in `inferred_customer_profile` JSONB: `offers`, `ideal_customers[]` (who/why/signal_keywords), `ideal_partners[]`, `anti_personas`. Fed into composite embedding text so similarity search reflects "who would buy from this person"; injected into ranking prompt with explicit weight hierarchy (EXPLICIT target_companies > AI-INFERRED ICP > BASELINE similarity); deterministic rerank adds +0.03/+0.05 when a candidate's profile contains 1/≥2 of the target's ICP signal keywords, +0.03 extra when the candidate's ICP also points back at the target (two-way fit = deal-ready). Company-similarity fallback surfaces up to 3 sector peers (shared vertical_tags or Grid sector) when no matches clear `MIN_MATCH_SCORE`, preventing empty briefings.
- **Data enrichment** — 73/73 attendees have AI summaries, embeddings, intent_tags, and vertical_tags; enrichment pipeline fully functional on EC2
- **1000 Minds speakers sync** — `speakers_sync.py` reads from `speakers` table (Jessica's curated list), upserts into `attendees` for matching; maps seniority→ticket_type, verticals→slugs, bio→goals; daily cron at 02:15 UTC; admin button on dashboard
- **Enhanced dashboard** — revenue tracking (€47.6k total, ticket breakdown), registration funnel (paid/failed/pending), weekly growth chart, attendee sources (Extasy/1000 Minds/self-registered), profile quality bars; live data from Extasy API with deduplication
- **1000minds vertical_tags** — 12 sector verticals (incl. `privacy`); display names aligned with 1000 Minds format; purple-styled tags visible on AttendeeMatches, Attendees, MyMatches; GPT responses validated against `VALID_VERTICALS`
- **The Grid B2B integration (active matching)** — `grid_enrichment.py` queries thegrid.id GraphQL API (public, no auth) by company name with retry + case-insensitive search; stores verified description, sector, products, socials in `enriched_profile["grid"]`; "Verified by The Grid" emerald card on match cards + profiles; Grid data feeds **actively** into matching: sector→vertical mapping for COMPLEMENTARY_VERTICALS scoring, products in GPT-4o candidate descriptions, product-pair boost in deterministic reranking; health check endpoint at `/dashboard/grid-health`
- **Sponsor Intelligence Reports** — admin dashboard section: select from 24 sponsors → generates personalised intelligence report (Grid → embed → pgvector → GPT-4o with overstating prevention); deterministic confidence scoring (0-1) based on data completeness; GPT forced to cite sources ([GRID], [GOALS], [PROFILE], [AI-INFERRED]) and flag sparse data; report shows relevance (HIGH/MEDIUM/LOW), conversation openers, deal potential, caveats, key evidence; CLI script also available at `backend/scripts/sponsor_intelligence.py`
- **Runa integration API** — 4 endpoints behind `X-API-Key` auth at `/api/v1/integration/*`: magic-link lookup (create-on-the-fly), ticket-purchased webhook, ticket-cancelled webhook, attendee-status check; spec doc at `docs/runa-integration-spec.md` + `.docx` for Swerve
- **AI Concierge markdown rendering** — assistant responses render with styled markdown (bold names, numbered lists, orange headers) via react-markdown; system prompt includes formatting instructions
- **Supabase synced** — full mirror of RDS: 38 attendees, 129 matches, all AI data; ready for migration cutover
- **Full attendee journey** — register (1-step form), browse matches, accept/decline with inline reason capture, mutual match confirmation, in-app messaging, meeting scheduling, ICS download, satisfaction rating
- **Role-based UI** — admin sees all attendees + matches read-only; attendees see only their own private briefing
- **POT brand design** — dark theme, `#E76315` orange, heading font, mobile-responsive (44px targets)
- **Email service** — AWS SES code shipped: new matches email, mutual match email, meeting confirmation, password reset; fire-and-forget, no-ops gracefully if unconfigured
- **Password reset** — self-service flow: forgot-password (rate-limited, no email enumeration) → SES email with 15-min JWT token → reset-password page with live validation → auto-redirect to login; no DB migration needed (stateless JWT tokens with `purpose: "reset"` claim)
- **Magic link access** — `magic_access_token` per attendee, `/m/:token` URL gives 1-click read-only match dashboard (no login required); tokens auto-generated on registration; admin bulk-generate via `POST /matches/generate-tokens`; match intro emails include magic link CTA
- **Architecture doc** — `docs/architecture-scale.md`: 3-stage pipeline scaling from 38→2,500 with pgvector IVFFlat, infrastructure upgrade path, runtime estimates
- **Cost analysis** — `docs/cost-analysis.md`: €0.39/attendee (optimised 2×/week refresh), under €0.50 target
- **Investor Heatmap** — `GET /dashboard/investor-heatmap` aggregates capital activity by sector (deploying_capital, co_investment, deal_making); horizontal bar chart + deal readiness summary on Dashboard
- **QR Business Card Exchange** — scannable QR on Profile page linking to attendee's magic link; copy link + save QR as PNG; uses react-qr-code
- **QR code in email** — match intro emails now include an inline QR code (base64 PNG) linking to the attendee's magic link dashboard
- **"Who do you want to meet?"** — new `target_companies` field on Attendee (free text); shown on Profile page + magic link enrichment card; fed into embeddings + GPT-4o ranking with highest priority per Z's direction
- **Magic link profile enrichment** — `PATCH /matches/m/{token}/profile` allows attendees to update Twitter + target_companies without login; enrichment card shown on MagicMatches page for incomplete profiles
- **Pre-Event Warm-Up Threads** — 11 auto-created vertical-based group discussion threads (tokenisation, DeFi, infrastructure, etc.); attendee's sectors highlighted and sorted first; "Threads" nav link for all authenticated users; 5s live polling
- **Social links on match cards** — LinkedIn, Twitter, and website icons on MyMatches so attendees can research their recommendations
- **Auth-aware home page** — logged-in users see "View your matches" / "Edit your profile"; logo links to /matches when authenticated
- **Saved shortlist** — bookmark per match card, All/Saved tab filter, persists in localStorage
- **Action model** — full-width filled "I'd like to meet" as dominant CTA; "Maybe later" as plain text link
- **Daily match refresh** — cron at 02:00 UTC
- **Profile photos** — user-uploaded only; AttendeeAvatar falls back to ui-avatars styled initials when no photo is set

## Infrastructure

- **Production URL**: `https://meet.proofoftalk.io` (Netlify frontend → Railway backend)
- **Backend**: **Railway** (`proofoftalkcd-production.up.railway.app`) — x-ventures Pro plan, auto-deploys from GitHub `main` branch, root dir `backend`
- **Database**: **Supabase PostgreSQL** (`db.mkcememoueziibbpqhfk.supabase.co:5432/postgres`) — XLabs Ext Pro plan, IPv4 add-on, shared with 1000 Minds (`speakers` table)
- **Email**: **Resend** — `matches@proofoftalk.io`, `proofoftalk.io` domain verified, production sending enabled, no sandbox restrictions
- **EC2 decommissioned**: was on personal AWS account; no longer in use
- **Deploy**: push to `main` → Railway auto-deploys backend; `npx netlify deploy --prod --dir=frontend/dist` for frontend

## Broken / Incomplete

- **Email template design** — match intro email is functional but needs design polish for production use (layout, branding, content)
- **generate-all HTTP timeout** — full match regeneration for all 80 attendees exceeds HTTP timeout; runs successfully in background but returns no response to caller; needs async job pattern for long-running operations

## Key Decisions Made

- **pgvector + GPT-4o hybrid** (not pure LLM) — pure LLM over N² pairs is too slow and expensive at 2,500 attendees; pgvector retrieves top-K candidates cheaply, GPT-4o only scores those — cost-effective without sacrificing match quality
- **Per-party status (status_a / status_b)** instead of single match status — enables two-sided consent UX; each attendee independently accepts/declines; correct mutual detection without extra tables
- **MIN_MATCH_SCORE = 0.60** — anything below is filtered before persisting; avoids padding attendees with weak connections that dilute the briefing
- **No automatic profile photo fetching** — GDPR compliance; the platform does not pull or store photos from LinkedIn or any third-party source; users upload their own photo URL if they choose to
- **Fire-and-forget email** — SES calls never raise to the caller; the product works without email, email is an enhancement layer; avoids adding failure modes to the match pipeline
- **localStorage for saved shortlist** — no backend change needed for demo; fast to ship, sufficient for a product demo at this stage

## Deployment

- **Production URL**: `https://meet.proofoftalk.io` (Netlify frontend + proxied API to EC2) — DNS restored 2026-04-01
- **Green EC2**: `3.239.218.239` — gunicorn + nginx; `APP_PUBLIC_URL=https://meet.proofoftalk.io`
- **Blue EC2** (fallback): `54.89.55.202` — old RDS connection (not updated)
- **Database**: **Supabase PostgreSQL** (`db.mkcememoueziibbpqhfk.supabase.co:5432/postgres`) — XLabs Ext Pro plan, IPv4 add-on enabled, shared project with 1000 Minds (`speakers` table). RDS backup saved as `.env.rds-backup` on EC2
- **Deploy command**: `bash deploy/push.sh 3.239.218.239 ~/Downloads/Credentials_Keys/pot-key.pem`
- **Integration API key**: set on EC2 in `.env` (`INTEGRATION_API_KEY`)

## Current Focus

- Privacy mode for anonymous/pseudonymous Web3 attendees (Jes's request)
- Share Runa integration spec + API key with Swerve
- Email provider switch — SES production denied; switch to Resend/SendGrid/Postmark (needs Victor + DNS access)
