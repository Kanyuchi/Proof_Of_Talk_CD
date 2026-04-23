# Project State — POT Matchmaker

**Last updated:** 2026-04-23 (LinkedIn enrichment restored via linkedin-api)
**Stack:** Python 3.12 / FastAPI / SQLAlchemy async · React 18 / TypeScript / Vite / Tailwind · **Supabase PostgreSQL** + pgvector · OpenAI (text-embedding-3-small + gpt-4o) · **Railway** (backend) · **Resend** (email) · Netlify (frontend)

---

## What's Working

- **3-stage AI matching pipeline** — Embed → pgvector retrieval → GPT-4o rank & explain; **234 matches** across 85 attendees, avg score **0.713**; vertical_tags + intent_tags + target_companies + inferred_customer_profile integrated into embeddings, GPT prompt, and deterministic reranking with COMPLEMENTARY_VERTICALS boost; ML feedback loop feeds decline reasons into GPT prompt
- **AI-inferred customer matching (Z's vision)** — each attendee gets a GPT-4o-inferred ICP stored in `inferred_customer_profile` JSONB: `offers`, `ideal_customers[]` (who/why/signal_keywords), `ideal_partners[]`, `anti_personas`. Fed into composite embedding text so similarity search reflects "who would buy from this person"; injected into ranking prompt with explicit weight hierarchy (EXPLICIT target_companies > AI-INFERRED ICP > BASELINE similarity); deterministic rerank adds +0.03/+0.05 when a candidate's profile contains 1/≥2 of the target's ICP signal keywords, +0.03 extra when the candidate's ICP also points back at the target (two-way fit = deal-ready). Company-similarity fallback surfaces up to 3 sector peers (shared vertical_tags or Grid sector) when no matches clear `MIN_MATCH_SCORE`, preventing empty briefings.
- **Data enrichment** — 73/73 attendees have AI summaries, embeddings, intent_tags, and vertical_tags; LinkedIn enrichment restored via `linkedin-api` library (free, email+password auth); enrichment pipeline: LinkedIn → website scrape → Grid B2B → AI summary → intent tags → embedding
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
- **Ferd outreach sheet sync (`POT Attendees` tab)** — Google Apps Script bound to `PoT26_Master_Email_Database_v3` polls Supabase via the read-only `attendees_sync` view every hour; mirrors 86 attendees into a `POT Attendees` tab plus a `POT Sync Log` tab for run metadata. Never touches `MERGED - All Investors` (which Ferd's `mergeInvestorTabs()` rebuilds on every run). Read-only anon key scoped to 6 columns; no write-back to Supabase. Repo copy of script at `docs/integrations/sheets_sync/Code.gs`.
- **Idempotent `ingest_extasy.py`** — `upsert_to_supabase()` now INSERTs new emails and PATCHes only Rhuna-authoritative fields (`extasy_order_id`, `extasy_ticket_code`, `extasy_ticket_name`, `phone_number`, `city`, `country_iso3`, `ticket_bought_at`, `ticket_type`) on existing rows via a diff-only PATCH. Enrichment data (`enriched_profile`, `ai_summary`, `embedding`, `interests`, `goals`, etc.) is never overwritten. Safe to re-run and safe to schedule.

## Infrastructure

- **Production URL**: `https://meet.proofoftalk.io` (Netlify frontend → Railway backend)
- **Backend**: **Railway** (`proofoftalkcd-production.up.railway.app`) — x-ventures Pro plan, auto-deploys from GitHub `main` branch, root dir `backend`
- **Database**: **Supabase PostgreSQL** (`db.mkcememoueziibbpqhfk.supabase.co:5432/postgres`) — XLabs Ext Pro plan, IPv4 add-on, shared with 1000 Minds (`speakers` table)
- **Email**: **Resend** — `matches@proofoftalk.io`, `proofoftalk.io` domain verified — **ALL 4 EMAIL TYPES CURRENTLY DISABLED** (`return` at top of each send function in `email.py`). Will re-enable when platform opens to attendees.
- **EC2 decommissioned**: was on personal AWS account; no longer in use
- **RDS stopped**: `pot-matchmaker` instance stopped 2026-04-15 with final snapshot `pot-matchmaker-preretire-20260415-0757`. AWS auto-restarts stopped instances after 7 days — consider deleting with final snapshot if not needed.
- **Deploy**: push to `main` → Railway auto-deploys backend; Netlify auto-deploys frontend (GitHub App relinked 2026-04-15)
- **Background jobs**: long-running admin actions (Grid re-enrich, sponsor reports) run as asyncio background tasks with `GET /dashboard/jobs/{id}` polling — no more 504 timeouts

## Broken / Incomplete

- **Email template design** — match intro email is functional but needs design polish for production use (layout, branding, content)
- **Grid coverage ceiling** — 23/85 attendees (27%) verified by The Grid. Remaining 62 are companies genuinely not indexed by Grid (confirmed via name + URL + email-domain probes). Would need Grid to expand their index or manual canonical-name dict for edge cases.
- **Attendee onboarding flow** — attendees like Pouneh Bligaard have Rhuna tickets but no user accounts on the platform. No self-serve path to get matches until emails are re-enabled or magic links are distributed.
- **Full email HTML templates** — morning schedule, D+1 wrap-up, D+7 nudge have function stubs but no HTML body yet (return-at-top blocks execution). Templates to be written when emails are re-enabled.

## Attendee Experience Phases (from docs/matchmaking-ux-integration.md)

| Phase | Status |
|---|---|
| 1. Instant (post-purchase magic link) | Blocked on Rhuna webhook go-live |
| 2. First Matches (24-48h email) | Blocked on Phase 1 |
| 3. Warm-Up (threads, messaging, scheduling) | Built |
| 4. Final Briefing (prep brief + PDF) | **Shipped** — `/m/:token/briefing` |
| 5. At-Event (morning email, QR, feedback) | Easy parts done, real-time = stretch |
| 6. Post-Event (contact export, follow-up) | **Shipped** — CSV export + email stubs |

## Key Decisions Made

- **pgvector + GPT-4o hybrid** (not pure LLM) — pure LLM over N² pairs is too slow and expensive at 2,500 attendees; pgvector retrieves top-K candidates cheaply, GPT-4o only scores those — cost-effective without sacrificing match quality
- **Per-party status (status_a / status_b)** instead of single match status — enables two-sided consent UX; each attendee independently accepts/declines; correct mutual detection without extra tables
- **MIN_MATCH_SCORE = 0.60** — anything below is filtered before persisting; avoids padding attendees with weak connections that dilute the briefing
- **No automatic profile photo fetching** — GDPR compliance; the platform does not pull or store photos from LinkedIn or any third-party source; users upload their own photo URL if they choose to
- **Fire-and-forget email** — SES calls never raise to the caller; the product works without email, email is an enhancement layer; avoids adding failure modes to the match pipeline
- **localStorage for saved shortlist** — no backend change needed for demo; fast to ship, sufficient for a product demo at this stage

## Deployment

- **Production URL**: `https://meet.proofoftalk.io` (Netlify frontend → Railway backend → Supabase)
- **Deploy**: push to `main` → Railway auto-deploys backend, Netlify auto-deploys frontend (GitHub App relinked 2026-04-15)
- **EC2 + RDS**: both decommissioned/stopped. RDS snapshot: `pot-matchmaker-preretire-20260415-0757`

## Current Numbers (2026-04-19)

- **85 attendees** in Supabase (after removing 6 seeds/test + merging 4 duplicate pairs)
- **234 matches** at avg score 0.713 (10 deal_ready / 21 non_obvious / 203 complementary)
- **23 Grid-verified** (27% coverage — confirmed ceiling via name + URL + email-domain probes)
- **Rhuna/Extasy**: 189 total orders, 102 valid (99 paid + 3 redeemed), ~€64k revenue
- **All emails disabled** until platform opens to attendees

## Current Focus

- Re-enable emails + attendee onboarding when platform is ready for attendees to sign in
- Sponsor intelligence rollout — Victor pitching pilot reports
- Schedule `ingest_extasy.py` on a cron for auto-sync
- Align CEO dashboard with matchmaker dashboard revenue figures
