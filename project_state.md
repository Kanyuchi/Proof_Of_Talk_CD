# Project State — POT Matchmaker

**Last updated:** 2026-04-01 (vertical tags aligned with 1000 Minds, Grid B2B integration, Runa API endpoints, DNS restored)
**Stack:** Python 3.12 / FastAPI / SQLAlchemy async · React 18 / TypeScript / Vite / Tailwind · PostgreSQL + pgvector on AWS RDS · OpenAI (text-embedding-3-small + gpt-4o) · AWS EC2 + SES · Netlify (frontend) · Supabase (DB — pending migration from RDS)

---

## What's Working

- **3-stage AI matching pipeline** — Embed → pgvector retrieval → GPT-4o rank & explain; **140 matches** across 38 attendees, avg score **0.70**, 36 above 0.75; vertical_tags + intent_tags integrated into embeddings, GPT prompt, and deterministic reranking with COMPLEMENTARY_VERTICALS boost
- **Data enrichment** — 38/38 attendees have AI summaries, embeddings, intent_tags, and vertical_tags; enrichment pipeline fully functional on EC2
- **1000minds vertical_tags** — 12 sector verticals (incl. `privacy`); display names aligned with 1000 Minds format; purple-styled tags visible on AttendeeMatches, Attendees, MyMatches; GPT responses validated against `VALID_VERTICALS`
- **The Grid B2B integration** — `grid_enrichment.py` queries thegrid.id GraphQL API (public, no auth) by company name; stores verified description, sector, socials in `enriched_profile["grid"]`; "Verified by The Grid" emerald card on match cards + profiles; Grid description included in embedding composite text
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

- **Production URL**: `https://meet.proofoftalk.io` (Netlify, live)
- **Backend**: green EC2 `3.239.218.239` — gunicorn + nginx; proxied via `netlify.toml`
- **Blue EC2** (`54.89.55.202`): still running as fallback; same RDS DB
- **Database**: AWS RDS PostgreSQL + pgvector (`eu-west-1`) — 38 attendees, 140 matches; Supabase synced (140 matches)

## Broken / Incomplete

- **SES email — BLOCKED** — AWS denied production access (case #177412752700989, 2026-03-23). Stuck in sandbox — can only send to individually verified emails. Need to switch to Resend/SendGrid/Postmark. Requires Victor approval + domain DNS access for `proofoftalk.io`
- **ML feedback loop not wired** — decline reasons and satisfaction scores are captured in DB but not fed back into future GPT ranking prompts
- **Supabase DB migration** — Supabase is synced as a mirror of RDS; backend still points to RDS; cutover to Supabase as primary not done yet

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
