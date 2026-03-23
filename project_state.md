# Project State — POT Matchmaker

**Last updated:** 2026-03-23 (41 attendees, 140 matches, magic link + QR + investor heatmap, architecture + cost docs, deployed to XVentures Netlify)
**Stack:** Python 3.12 / FastAPI / SQLAlchemy async · React 18 / TypeScript / Vite / Tailwind · PostgreSQL + pgvector on AWS RDS · OpenAI (text-embedding-3-small + gpt-4o) · AWS EC2 + SES · Netlify (frontend) · Supabase (DB — pending migration from RDS)

---

## What's Working

- **3-stage AI matching pipeline** — Embed → pgvector retrieval → GPT-4o rank & explain; **140 matches** across 38 attendees, avg score **0.70**, 36 above 0.75; vertical_tags + intent_tags integrated into embeddings, GPT prompt, and deterministic reranking with COMPLEMENTARY_VERTICALS boost
- **Data enrichment** — 38/38 attendees have AI summaries, embeddings, intent_tags, and vertical_tags; enrichment pipeline fully functional on EC2
- **1000minds vertical_tags** — 11 sector verticals; 38/38 attendees classified by GPT-4o; 9/11 verticals represented; `COMPLEMENTARY_VERTICALS` map drives cross-sector boost in reranking
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

- **SES email — sandbox mode** — `matches@proofoftalk.io` verified as sender in EU-WEST-1; password reset email confirmed working end-to-end; production access requested (case #177412752700989, awaiting AWS approval); until approved, can only send to individually verified recipients
- **ML feedback loop not wired** — decline reasons and satisfaction scores are captured in DB but not fed back into future GPT ranking prompts
- **Supabase DB migration** — Supabase is synced as a mirror of RDS; backend still points to RDS; cutover to Supabase as primary not done yet

## Key Decisions Made

- **pgvector + GPT-4o hybrid** (not pure LLM) — pure LLM over N² pairs is too slow and expensive at 2,500 attendees; pgvector retrieves top-K candidates cheaply, GPT-4o only scores those — cost-effective without sacrificing match quality
- **Per-party status (status_a / status_b)** instead of single match status — enables two-sided consent UX; each attendee independently accepts/declines; correct mutual detection without extra tables
- **MIN_MATCH_SCORE = 0.60** — anything below is filtered before persisting; avoids padding attendees with weak connections that dilute the briefing
- **No automatic profile photo fetching** — GDPR compliance; the platform does not pull or store photos from LinkedIn or any third-party source; users upload their own photo URL if they choose to
- **Fire-and-forget email** — SES calls never raise to the caller; the product works without email, email is an enhancement layer; avoids adding failure modes to the match pipeline
- **localStorage for saved shortlist** — no backend change needed for demo; fast to ship, sufficient for a product demo at this stage

## Current Focus

- Full end-to-end journey test — accept match, mutual match, messaging, meeting scheduling
- SES production access — awaiting AWS approval (case #177412752700989); password reset email verified working in sandbox
