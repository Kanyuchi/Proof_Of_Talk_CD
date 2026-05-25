# Session Log — POT Matchmaker

Append-only. Never delete entries. Oldest at top, newest at bottom.

---

## 2026-03-07 14:00 — Initial scaffold: FastAPI backend + React frontend

- Created `backend/` with FastAPI, SQLAlchemy async, Alembic migrations, pgvector
- Created `frontend/` with React 18, TypeScript, Vite, Tailwind CSS, React Query
- Set up AWS RDS PostgreSQL with pgvector extension
- Seeded 5 fictional attendee profiles from the XVentures case study

## 2026-03-07 17:30 — 3-stage AI matching pipeline

- Built `backend/app/services/matching.py`: Embed → Retrieve → Rank & Explain
- OpenAI `text-embedding-3-small` for attendee profile embeddings (1536-dim)
- pgvector cosine distance (`<=>`) for candidate retrieval
- GPT-4o re-ranking for complementarity, deal-readiness, non-obvious connections
- MIN_MATCH_SCORE = 0.60 threshold to filter weak matches

## 2026-03-08 10:00 — Role-based UI and admin-gated Attendees page

- Attendees list page gated to `is_admin` role — attendees can browse profiles, admin read-only on matches
- Role-based nav: different items shown depending on user role
- Attendee matches marked private — non-admin only sees their own matches

## 2026-03-08 15:00 — In-app messaging and scheduled appointments

- Enabled threaded in-app messages for mutual matches
- Added "Your Schedule" timeline in MyMatches showing booked meetings in chronological order

## 2026-03-09 11:00 — Fixes: messaging empty state, URL validation, mobile

- Fixed messages empty state to explain mutual-accept requirement with shortcut to matches
- Added URL validation with auto `https://` prepend on blur (Register + profile edit)
- Mobile pass: `min-h-[44px]` touch targets, responsive grid layouts

## 2026-03-10 09:00 — Iter-13: intro messages, Extasy sync, photo pipeline, POT brand

- Intro message (icebreaker) auto-send on match accept
- Extasy daily sync wired; daily match refresh cron at 02:00 UTC
- AttendeeAvatar component: fallback chain explicit → Gravatar → Clearbit → initials
- POT brand design: `#E76315` orange, `#0d0d1a` dark, heading font, badge components
- Replaced `window.prompt()` decline with inline textarea panel — no native prompts

## 2026-03-10 16:00 — Fix: meeting scheduling and success/failure states

- Meeting scheduler: slot picker for June 2–3, ICS `.ics` download
- Success/failure states added to all async actions (accept, schedule, feedback)
- "Accept Meeting" / "Not Now" language in place at this point

## 2026-03-11 12:00 — Extasy live pipeline: 16 real attendees ingested

- Created `backend/scripts/pipeline_live.py`: fetches Extasy paid attendees → REST → enrichment → matching
- 16 real attendees loaded into RDS (23 total including 7 seed profiles)
- Hit OpenAI quota limit (429) on EC2 — enrichment/embedding/match-gen blocked; requires top-up

## 2026-03-16 14:30 — Feedback sprint: language, action model, email, shortlist, registration

- **AttendeeMatches.tsx**: `"WHY YOU SHOULD MEET"` → `"Why this meeting matters"` — consistent language
- **AttendeeMatches.tsx + MyMatches.tsx**: `"Accept Meeting"` / `"Not Now"` → full-width filled `bg-emerald-500` "I'd like to meet" as dominant CTA; `"Maybe later"` demoted to plain text link — removes equal-weight button competition
- **MyMatches.tsx**: Added bookmark/save per match card; `All` / `Saved (n)` tab filter; state persists in `localStorage` under `pot_saved_matches`
- **AttendeeAvatar.tsx**: Replaced deprecated Clearbit (`logo.clearbit.com`) with `ui-avatars.com` — always renders styled POT-branded initials, no dependency on external logo API
- **Register.tsx**: Collapsed 3-step wizard (9 fields) → 1-step form (email, password, name, LinkedIn URL, goals) — removed company, title, company_website, seeking, interests, confirmPassword
- **AuthContext.tsx + client.ts**: `RegisterData` fields company/title/ticket_type/interests/goals made optional to match new form
- **backend/app/services/email.py** (new): AWS SES email service — `send_match_intro_email`, `send_mutual_match_email`, `send_meeting_confirmation_email`; fire-and-forget, silent no-op if `AWS_SES_FROM_EMAIL` not set
- **backend/app/core/config.py**: Added `AWS_SES_FROM_EMAIL: str = ""`
- **backend/app/services/matching.py**: Hooked match intro email at end of `generate_matches_for_attendee`
- **backend/app/api/routes/matches.py**: Mutual match email on `status → accepted`; meeting confirmation email on `PATCH /schedule`
- **backend/app/schemas/auth.py**: `company`, `title` default `""`, `no_empty_strings` scoped to `name` only
- Deployed to green EC2 (3.239.218.239); TypeScript clean, Python syntax clean, migrations ran, service healthy

## 2026-03-16 16:15 — Extasy sync verified, enrichment confirmed, pipeline default updated to green

- Ran `pipeline_live.py --dry-run`: Extasy now has 21 paid attendees (up from 16 last run); all 21 already in DB (total 34 — 21 Extasy + 7 seed + 6 other)
- Both blue (54.89.55.202) and green (3.239.218.239) share the same RDS — data is identical on both servers
- Verified directly on EC2: 34/34 attendees have embeddings + AI summaries; 121 matches at avg score 0.69; enrichment fully functional
- 504 errors seen via pipeline script are nginx proxy timeouts on long-running batch HTTP calls — operations complete on EC2, nginx drops the connection first; not an enrichment failure
- Updated `pipeline_live.py` default target from blue → green (`http://3.239.218.239`); added `"blue"` as named target

## 2026-03-17 15:35 — Netlify production domain + SES activation + green EC2 503 fix

- **Context**: Manager deployed frontend to Netlify at `https://meet.proofoftalk.io` with Supabase DB; green EC2 (3.239.218.239) is the backend; `netlify.toml` proxies `/api/*` → green EC2
- **Root cause of 503 on /attendees**: FastAPI trailing-slash redirect (`307 Location: http://localhost:8000/api/v1/attendees/`) — Netlify proxy couldn't follow a redirect pointing to localhost → 503
- **Fix**: Added `proxy_redirect http://127.0.0.1:8000/ /;` to nginx — rewrites Location to relative path; Netlify can now follow the redirect
- **Green EC2 .env updated**: Added `https://meet.proofoftalk.io` to `ALLOWED_ORIGINS`; set `APP_PUBLIC_URL=https://meet.proofoftalk.io`
- **SES activation**: `APP_PUBLIC_URL` made an env var in `config.py` (was hardcoded EC2 IP); all 3 email functions default to `settings.APP_PUBLIC_URL`; `.env.example` updated
- **`netlify.toml`**: Confirmed correct — proxies `/api/*` → `http://3.239.218.239`; SPA fallback in place
- **whats_next.md**: Item #8 GDPR decision consolidated in Done ✓; item #19 transparency cues added to Soon
- Deployed latest code to green EC2; nginx reloaded; service healthy

## 2026-03-17 16:05 — Fix Netlify 503: attendees route trailing-slash redirect

- **Root cause**: FastAPI routes defined as `"/"` trigger a 307 redirect to `<scheme>://<host>/api/v1/attendees/`; nginx `proxy_redirect` could not rewrite it because FastAPI uses the `Host` header (`3.239.218.239`) to build the URL, not `localhost:8000`; Netlify passed the 307 to the browser which blocked `http://3.239.218.239/...` as mixed content → original 503
- **Fix**: Changed `@router.get("/")` and `@router.post("/")` in `attendees.py` to `""` — no redirect is issued; endpoint responds directly to `/api/v1/attendees`
- **Also cleaned**: removed unused `proxy_redirect` directive from `deploy/nginx.conf`
- **Verified**: `https://meet.proofoftalk.io/api/v1/attendees` now returns 401 (correct — needs auth token); 503 gone

## 2026-03-20 — Friday weekly update email

- Created `docs/friday-update-2026-03-20.md` — weekly update for team covering 2026-03-17 → 2026-03-20
- Content: production domain live, Supabase sync complete, 1000minds verticals shipped, comp tickets included, 503 fix
- Numbers: 38 attendees, 129 matches, 100% enrichment, 9/11 verticals represented
- Feedback asks: vertical accuracy, Extasy order count confirmation, vertical visibility decision, priority call on verticals vs onboarding

## 2026-03-20 — Progress Report iter-14

- Created `Matchmaking_Feedback/feedback-progress-report-iter14.html` — updated progress report matching iter-13 format
- Generated `Matchmaking_Feedback/POT_Matchmaker_Progress_Report_iter14.pdf` via Chrome headless
- Changes from iter-13: #14 Pending→Partial (SES email), #16 Pending→Partial (SES templates), #19 Pending→Done (saved shortlist)
- Nice to Have: 2.5/8 (31%) → 4.5/8 (56%); Overall: 79% → 84%
- Added "What Changed" section, "By the Numbers" block, 4 new Beyond the Brief items (production domain, Supabase sync, 1000minds verticals, comp ticket pipeline)

## 2026-03-20 — Matching engine enhancement + AI concierge markdown rendering

- **embeddings.py**: Added `vertical_tags` and `intent_tags` to `build_composite_text()` — these signals were classified for all 38 attendees but never fed into embeddings
- **matching.py**: Added `COMPLEMENTARY_VERTICALS` map (11 verticals with cross-sector affinities), vertical_tags in GPT-4o ranking prompt (both target + candidate descriptions), cross-sector instruction, and vertical affinity boost in `_deterministic_rerank()` (+0.04 complementary, +0.02 same-sector)
- **concierge.py**: Added vertical_tags to `_brief_attendee_line()` context, markdown formatting instructions to system prompt, vertical_tags to sector filter in `_apply_tool_filters()`
- **ChatPanel.tsx**: Replaced raw `{msg.content}` with `<MarkdownMessage>` component for styled markdown rendering
- **MarkdownMessage.tsx**: New component — renders assistant messages with react-markdown; styled bold, headers, lists matching POT brand
- Installed `react-markdown` dependency
- Frontend build verified clean
- **Deployed**: backend to green EC2 (`3.239.218.239`), frontend auto-deployed to Netlify (site `gregarious-kitsune-d44915`)
- **Re-embedded**: nulled all 38 embeddings, re-ran `process_all_attendees()` — embeddings now include vertical_tags + intent_tags
- **Re-matched**: `run_matching_pipeline()` produced 140 matches (was 129), avg score 0.700 (was 0.69), 36 above 0.75; 103 complementary, 19 non_obvious, 18 deal_ready
- **Supabase synced**: cleared old 129 matches, inserted 140 new matches via REST API (3 batches of 50/50/40)
- **Smoke tested**: health check OK, registration works, concierge returns markdown-formatted response (### headers, **bold** names, numbered lists), matches endpoint returns results, frontend serves react-markdown bundle
- **SES email setup**: IAM `AmazonSESFullAccess` attached, `AWS_SES_FROM_EMAIL=matches@proofoftalk.io` set on EC2, service restarted; SES identity created in us-east-1 — pending email verification click (or domain verification as alternative)

## 2026-03-21 — Password reset flow (full stack)
- **Backend `security.py`**: Added `create_reset_token()` (15-min JWT with `purpose: "reset"`) and `decode_reset_token()` — stateless, no DB migration needed
- **Backend `schemas/auth.py`**: Added `ForgotPasswordRequest` and `ResetPasswordRequest` with password strength validator
- **Backend `routes/auth.py`**: Added `POST /auth/forgot-password` (rate-limited 3/min, no email enumeration) and `POST /auth/reset-password` (validates token, updates password)
- **Backend `services/email.py`**: Added `send_password_reset_email()` — branded HTML template matching existing POT email style
- **Frontend `client.ts`**: Added `forgotPassword()` and `resetPassword()` API functions
- **Frontend `ForgotPassword.tsx`**: New page — email form → success state with "check your email" message
- **Frontend `ResetPassword.tsx`**: New page — reads `?token=` from URL, new password + confirm with live validation, auto-redirect to login on success
- **Frontend `Login.tsx`**: Added "Forgot password?" link below password field
- **Frontend `App.tsx`**: Added `/forgot-password` and `/reset-password` routes
- All imports verified, TypeScript compiles clean, reset token round-trip tested
- **Concierge chat style overhaul**: rewrote system prompt to produce conversational, chat-friendly responses instead of report-style output — no more `###` headers, shorter per-person blurbs, ends with follow-up question. Updated `MarkdownMessage.tsx` — names render in orange (`#E76315`), better spacing, relaxed line-height, softer list markers, link support

## 2026-03-21 17:30 — Deploy to pot-matchmaker (XVentures Netlify)
- Relinked Netlify CLI from personal `gregarious-kitsune-d44915` to XVentures `pot-matchmaker` site
- Built frontend and deployed to production via `netlify deploy --prod --dir=frontend/dist`
- Verified: `meet.proofoftalk.io` now serves new bundle (`index-CmmrY8cL.js`) with password reset flow + concierge improvements
- Verified: `POST /api/v1/auth/forgot-password` returns correct response through Netlify proxy → green EC2
- Updated `deploy/push.sh` to include Netlify deploy step after EC2 sync (with graceful fallback if CLI not installed)

## 2026-03-22 — SES sender verification + production access request
- Verified `matches@proofoftalk.io` as SES sender identity in EU-WEST-1 (Ireland) — status: Verified
- Submitted SES production access request (support case #177412752700989) — mail type: Transactional, daily quota: 1,000, awaiting AWS approval (~24h)
- Until production access is granted, SES is in sandbox mode: can only send to individually verified recipient addresses
- Verified `shaun@proofoftalk.io` as test recipient
- **Password reset email confirmed working** — branded email arrives from `matches@proofoftalk.io` via SES, POT orange CTA button, 15-min token expiry, full round-trip tested

## 2026-03-23 — Magic link access + architecture doc + cost analysis
- **Magic link (no-login access)**: Added `magic_access_token` field to Attendee model, Alembic migration, `GET /matches/m/{token}` endpoint (no auth required), `POST /matches/generate-tokens` admin endpoint to bulk-generate tokens, frontend `/m/:token` route with read-only match dashboard (`MagicMatches.tsx`). Auto-generates token on registration. Email CTA links now use magic link when available. Satisfies KR 2.2 (≤2 extra questions) and KR 2.3 (1-click access).
- **Architecture & scale doc** (`docs/architecture-scale.md`): 3-stage pipeline breakdown, scaling analysis from 38→2,500 profiles, pgvector IVFFlat index strategy, infrastructure upgrade path, pipeline runtime estimates. Satisfies KR 3.2.
- **Cost analysis doc** (`docs/cost-analysis.md`): Per-attendee cost breakdown (onboarding $0.005, match gen $0.028/run, enrichment $0.01), optimised total €0.39/attendee at 2,500 with 2×/week refresh — under €0.50 target. Satisfies KR 3.3.
- **Deployed** to green EC2 (`3.239.218.239`) + Netlify (`meet.proofoftalk.io`). Migration `e5a8f3c21d99` applied. Generated magic tokens for all 41 attendees. Verified magic link end-to-end: `GET /matches/m/{token}` returns matches without auth (tested with Sebastien Borget — 7 matches rendered in browser).
- **Wired magic_token into match pipeline email** — `send_match_intro_email` call in `matching.py` now passes `attendee.magic_access_token`, so match intro emails will contain the 1-click `/m/{token}` link instead of `/matches` (login-required). Blocked on SES production access (case #177412752700989).
- **Home page auth-aware** — logged-in users see "View your matches" + "Edit your profile" instead of sign-in/register CTAs; logged-out users still see the original CTAs
- **Rewrote "How the Engine Works" copy** — removed technical jargon ("semantic embeddings", "GPT-4o") from the 3 feature cards; descriptions now attendee-facing and explain the value, not the tech
- **Social links on match cards** — MyMatches now shows LinkedIn, Twitter, and website icons for each recommended person so attendees can research their matches before the event
- **SES verification emails sent** to mona@proofoftalk.io, nupur@proofoftalk.io, hamid@xventures.de, victor@xventures.de, z@xventures.de — awaiting clicks
- **Investor Heatmap** — new `GET /dashboard/investor-heatmap` endpoint aggregates attendees by vertical_tags × capital intents (deploying_capital, co_investment, deal_making); Dashboard renders horizontal bar chart with deal readiness summary (high/medium/low) and per-sector capital activity
- **QR Business Card Exchange** — `GET /auth/my-magic-link` returns user's magic token; new `QRCard` component on Profile page renders scannable QR code linking to `/m/{token}`; copy link + save QR as PNG buttons; uses react-qr-code package
- **Pre-Event Warm-Up Threads** — Thread + ThreadPost models, migration `f7b2a9c43e11`, 11 auto-created vertical-based threads (tokenisation, DeFi, infrastructure, AI/DePIN, etc.); list + detail + post endpoints; `Threads.tsx` page with live polling; nav link for all authenticated users; attendee's sectors highlighted and sorted first

## 2026-03-25 — QR in email + "who do you want to meet" + profile enrichment
- **QR code in match intro email** — `_generate_qr_data_uri()` generates base64 PNG QR code inline in HTML email linking to magic link; shows below CTA button with "Or scan to open on your phone"
- **target_companies field** — new `target_companies` (free text) on Attendee model, migration `a1c9d5e72f33`, added to schemas + AttendeeResponse; "Who do you want to meet?" textarea on Profile page
- **Magic link profile enrichment** — `PATCH /matches/m/{token}/profile` accepts Twitter + target_companies without JWT; MagicMatches page shows enrichment card for attendees with incomplete profiles
- **Matching pipeline integration** — target_companies included in embedding composite text (`embeddings.py`) and GPT-4o ranking prompt (`matching.py`) with explicit high-priority instruction per Z's weight hierarchy (explicit > AI-inferred > baseline)
- **Zohair product direction saved to memory** — AI-inferred customer matching, "who do you want to meet" field, company similarity fallback, post-purchase email funnel, weight hierarchy

## 2026-03-26 — Quick UX wins: nav badge + ML feedback + match card buttons
- **Mutual match nav badge** — `GET /matches/pending-count` counts matches where other party accepted but user hasn't responded; orange badge on My Matches nav item (desktop + mobile), polled every 30s
- **ML feedback loop** — GPT-4o ranking prompt now includes up to 5 prior decline reasons as negative examples; instructs model to "avoid similar matches"
- **Match card feedback buttons** — ThumbsUp "More like this" (accepts + tags `FEEDBACK:more_like_this`) and ThumbsDown "Not relevant" (declines + tags `FEEDBACK:not_relevant`) on pending match cards for lightweight quality signals

## 2026-03-29 — Customer journey diagram + Friday update
- **Customer journey Mermaid diagram** (`docs/customer-journey.md`) — complete flowchart covering: ticket purchase → Extasy sync → enrichment pipeline → 3-stage matching → email with QR → magic link → profile enrichment → match interaction → mutual match → chat → meeting scheduler → feedback loop → daily refresh. Also covers warm-up threads, QR business card, organiser dashboard.
- **Friday update** (`docs/friday-update-2026-03-28.md`) — weekly update covering 2026-03-21 → 2026-03-28; key results: all 5 Quick Wins shipped, magic link live, Z's product direction implemented, architecture + cost docs delivered; OKR scorecard: 5/6 done (only 50-profile scale test pending)

## 2026-03-30 — Directory cleanup
- Deleted Word temp files (`~$*.docx`), `.DS_Store` files, empty `images/` dir, frontend placeholder docs
- Moved `brella.md` → `docs/`, generator scripts → `docs/scripts/`
- Consolidated `docs/node_modules` into root `package.json`

## 2026-03-31 — DNS diagnosis + vertical tags alignment with 1000 Minds
- **DNS issue diagnosed**: `meet.proofoftalk.io` CNAME record missing (NXDOMAIN); Netlify app is fine, just the DNS signpost is gone. EC2 at `http://3.239.218.239` used as temporary fallback.
- **Privacy vertical added**: new `privacy` tag (ZK proofs, confidential computing) — added to GPT-4o classification prompt, COMPLEMENTARY_VERTICALS (bidirectional with infra/DeFi/policy)
- **Vertical display names**: `backend/app/core/constants.py` — canonical 12-vertical taxonomy with display names matching 1000 Minds format
- **Frontend vertical tags surfaced**: purple-styled tags now visible on AttendeeMatches, Attendees list, and MyMatches cards; display name utility in `frontend/src/utils/verticals.ts`
- **Validation**: GPT-4o responses now filtered against `VALID_VERTICALS` to prevent hallucinated tags
- Deployed to green EC2 + Netlify
- **Runa integration spec** (`docs/runa-integration-spec.md` + `.docx`) — API specification for Swerve to integrate matchmaker into Runa
- **Runa integration endpoints built + deployed** — 4 endpoints behind X-API-Key auth:
  - `GET /integration/magic-link` — lookup or create-on-the-fly by email (returns magic link URL)
  - `POST /integration/ticket-purchased` — real-time webhook from Runa (idempotent)
  - `POST /integration/ticket-cancelled` — deactivation webhook
  - `GET /integration/attendee-status` — match count, mutual matches, profile status
- Added `INTEGRATION_API_KEY` to config, `require_api_key` dependency, CORS `X-API-Key` header
- API key set on EC2, all endpoints verified live

## 2026-03-31 (cont.) — The Grid B2B data integration
- **New `grid_enrichment.py`** — GraphQL client for thegrid.id public API (no auth needed). Searches `profileInfos` by company name, extracts: verified description, sector, socials (LinkedIn/Twitter/Telegram/YouTube), URLs, founding date, profile type.
- **Enrichment pipeline** — Grid added as final enrichment source after Crunchbase in `enrichment.py`. Cached in `enriched_profile["grid"]`.
- **Embeddings** — Grid description + sector included in composite text for vector embeddings (improves match quality for Web3 companies in Grid).
- **Frontend** — "Verified by The Grid" card (emerald green) on MyMatches, MagicMatches, AttendeeMatches showing company description, sector badge, and link to Grid profile.
- Deployed to EC2 + Netlify

## 2026-04-01 — DNS restored + production URL fix
- **`meet.proofoftalk.io` DNS is back** — CNAME record re-added by Swerve, domain resolving and serving correctly via Netlify
- **`APP_PUBLIC_URL` restored** to `https://meet.proofoftalk.io` on EC2 (was temporarily set to EC2 IP for Swerve testing while DNS was down)
- Magic links now return production URLs again
- All features from 2026-03-30/31 (vertical tags, Grid integration, Runa API) confirmed live on production domain

## 2026-04-01 (cont.) — Privacy mode for anonymous/pseudonymous profiles
- **`privacy_mode` field** on Attendee model — `"full"` (default) or `"b2b_only"`; migration adds column with server_default
- **Backend redaction** — `redact_for_privacy()` in schemas strips name, email, photo, title, LinkedIn, Twitter from API responses for b2b_only attendees; shows company name as identifier instead
- **Mutual-match reveal** — personal info automatically revealed when both parties accept the match (checked in match API response layer)
- **Settable everywhere** — registration, profile update (PUT /auth/profile), magic link profile (PATCH /matches/m/{token}/profile)
- **Frontend** — "B2B Profile" badge on MyMatches + MagicMatches cards; title displays company-only when null; Profile page has toggle switch with explanation
- **Email** — match intro emails use company name instead of personal name for b2b_only attendees; mutual match emails reveal names (both consented)
- Deployed to EC2 + Netlify

## 2026-04-01 (cont.) — Full Grid org card widget
- **Expanded Grid enrichment** — 2-stage GraphQL query: stage 1 fetches profile (media/logos, tagLine, descriptionLong), stage 2 fetches products + legal entities via rootId
- **GridOrgCard component** (`frontend/src/components/GridOrgCard.tsx`) — reusable widget replacing inline compact cards:
  - **Compact view** (always visible): company logo, "Verified by The Grid" badge, sector badge, type badge, tagline, short description
  - **Expanded view** (toggle): full description, social links (Twitter, Discord, GitHub, Telegram, etc.), products (name, type, main flag, description), legal entities (name, type, country), founded date, Grid profile link
- Replaces inline Grid cards in MyMatches, MagicMatches, AttendeeMatches
- Deployed to EC2 + Netlify

## 2026-04-01 (cont.) — Enrichment data quality fix
- **Grid matching improved** — company name normalization (split concatenated words like "Cardanofoundation" → "Cardano"), domain-based fallback search, word-boundary validation to reject false positives ("Atos" no longer matches "Satoshigallery"), minimum 4-char search term
- **Batch re-enrichment** — ran Grid enrichment for all 56 attendees: **15/56 matched** (up from 2). Matches include: Kraken, KuCoin, The Sandbox, Cardano, Proof of Talk, SoftStack, Carbon Ratings, Summ, BABS, XVentures
- 30 attendees have no Grid match (their companies aren't in The Grid database yet — niche/small Web3 companies)
- 11 skipped (company name too short or empty)

## 2026-04-02 — Supabase migration complete
- **Database migration**: RDS PostgreSQL → Supabase PostgreSQL (full cutover)
- **Schema prepared**: added missing columns (magic_access_token, target_companies, privacy_mode, photo_url), created missing tables (conversations, messages, threads, thread_posts), stamped Alembic at 6a28b2ff60c9
- **Data migrated**: 60 attendees, 144 matches, 10 users, 3 conversations, 2 messages, 11 threads, 1 thread post — all from RDS via Python asyncpg script
- **Enum fix**: Supabase had lowercase tickettype enum (delegate/sponsor/speaker/vip), RDS had uppercase; renamed enum values to uppercase to match SQLAlchemy model
- **IPv4 add-on**: enabled on Supabase Pro plan ($4/mo) — EC2 couldn't reach Supabase's IPv6-only direct connection; IPv4 add-on resolved this
- **EC2 .env updated**: DATABASE_URL now points to `db.mkcememoueziibbpqhfk.supabase.co:5432/postgres`; RDS backup saved as `.env.rds-backup`
- **Verified**: health, login, dashboard stats (60 attendees, 144 matches, 0.700 avg), threads (11), investor heatmap (11 sectors), both `meet.proofoftalk.io` and `3.239.218.239` working
- **1000 Minds integration**: speakers table (9 rows from Jessica) accessible in same Supabase project; speakers → attendees sync to be built next
- **Speakers → attendees sync built** — `speakers_sync.py` reads from `speakers` table (1000 Minds), upserts into `attendees` for matching. Maps seniority→ticket_type, verticals→slugs, bio→goals, image→photo. Dedup by name+company (case-insensitive). `POST /dashboard/sync-speakers` admin endpoint. Daily cron at 02:15 UTC. First run: 8/8 speakers synced (68 total attendees). Re-run: 0 inserted, 8 skipped (idempotent).

## 2026-04-03 — Admin view parity + dashboard enhancement + Supabase sync
- **Admin match cards parity** — AttendeeMatches (admin view) match cards now show social links (LinkedIn/Twitter/website), purple vertical tag badges, and Grid B2B verified company card — matching what attendees see on MyMatches
- **Enhanced dashboard — iteration 1** — new `GET /dashboard/revenue` endpoint pulls live Extasy data; added Revenue KPIs (€42,554 total, 68 tickets, 54.8% conversion, €1,330 avg), Registration Funnel (paid/redeemed/failed/pending/refunded), Revenue by Ticket Type, Weekly Growth chart, Attendee Sources (Extasy/1000 Minds/self-registered), Profile Quality bars (goals/LinkedIn/Twitter/website/Grid/photo/targets)
- **Dashboard polish — iteration 2** — Sync Speakers button (purple) in admin actions, revenue numbers no longer truncated, week labels readable ("Mar 10" not "2026-W11"), source label "Self-registered" instead of "Other/Manual", profile quality bars with percentages inside
- **Extasy sync ran** — 0 new inserts, all 50 real Extasy attendees already in DB
- **Match generation** — 317 matches across 73 attendees, avg score 0.704, all on Supabase
- **Grid card on admin view** — confirmed working for attendees with Grid data (19/73); Martin Quensel has no Grid data because Centrifuge isn't in The Grid database

## 2026-04-07 — Commercial strategy: matchmaking as revenue driver
- **Strategy research** — deep analysis of how matchmaking/Grid can drive ticket sales (pre-purchase preview, VIP upsell, referral QR), multiply sponsorship value (Intelligence Packages €5-50k/sponsor, priority matching, sponsored intros, ROI reports), and lock post-event retention
- **Revenue pitch HTML** (`docs/matchmaking-revenue-pitch.html`) — concise internal strategy brief for marketing team; covers 3 revenue levers, sponsor tier pricing (€225k potential at 15 sponsors), unfair advantages (Grid + AI + intent data), and action items per team member

## 2026-04-07 — Railway migration + Resend email activation
- **Railway deployment** — backend migrated from personal AWS EC2 to Railway (x-ventures Pro plan); service at `proofoftalkcd-production.up.railway.app`; root dir `backend`, uvicorn start command, all env vars configured
- **Netlify proxy updated** — `netlify.toml` now proxies `/api/*` to Railway instead of EC2 IP; deployed to `meet.proofoftalk.io`
- **Resend email activated** — switched from AWS SES (sandbox, blocked) to Resend (Pro account, `proofoftalk.io` domain verified); all 3 email functions migrated (match intro, mutual match, meeting confirmation); test email confirmed delivered to `shaun@proofoftalk.io`
- **EC2 decommissioned** — no more personal AWS dependency; all infrastructure now on company accounts (Railway, Supabase, Netlify, Resend)
- **Match generation on Railway** — needs investigation; GPT-4o calls may timeout; read endpoints work fine
- **QR code fixed in email** — Gmail blocks base64 data URIs and CID attachments; switched to quickchart.io hosted QR API URL (`https://quickchart.io/qr?text=...`); renders inline in all email clients including Gmail
- **OpenAI API key fixed on Railway** — original key was rejected (401); new key set in Railway variables; match generation confirmed working (4 matches generated for test attendee)
- **Match pipeline on Railway verified** — process-all (5 attendees processed), generate single attendee (4 matches), Extasy sync (4 new inserted, 75 valid total); all working
- **Email confirmed delivered** — match intro email with QR code, "Our Matchmaker" copy, and magic link CTA received at shaun@proofoftalk.io via Resend; no more SES sandbox restrictions

## 2026-04-07 21:30 — Email deliverability feedback (Yannik/Softstack)
- **Issue**: Microsoft flagging match emails as junk — domain alignment mismatch (From: proofoftalk.io but Return-Path/bounce goes to amazonses.com)
- **Root cause**: Missing DMARC record on proofoftalk.io DNS
- **DNS fix needed** (by domain manager): add TXT record `_dmarc.proofoftalk.io` → `v=DMARC1; p=quarantine; rua=mailto:dmarc@proofoftalk.io; pct=100; adkim=r; aspf=r`
- **DKIM and SPF already verified** via Resend (send.proofoftalk.io subdomain)
- **From name updated** to `Proof of Talk <matches@proofoftalk.io>` for better trust signals
- **Domain warm-up**: gradual sending (not mass blast) to build reputation — already following this approach
- **Positive feedback**: Yannik said "really cool idea with the matchmaking"
- **DMARC record live** — Victor added TXT record to proofoftalk.io DNS; verified propagated; Microsoft junk flagging should resolve

## 2026-04-08 — Fix revenue double-counting in dashboard + update pitch figures
- **Bug**: Dashboard revenue endpoint (`/api/v1/dashboard/revenue`) was summing raw Extasy API orders without deduplication — same email + same ticket + same amount counted multiple times (e.g. Tommi Vuorenmaa's duplicate Startup Pass = €599 overcounted)
- **Fix**: Added deduplication in `backend/app/api/routes/dashboard.py` — key on `(email, ticket_name, amount)`, keeps first occurrence, drops true duplicates while preserving legitimate multi-ticket purchases (e.g. Francisco/Yaroslav on same email with different ticket types)
- **Result**: Revenue now matches Google Sheets: €47,590.75 (was €48,189.75 before dedup; Google Sheets = €47,591)
- **Pitch updated**: `docs/matchmaking-revenue-pitch.html` — revenue €42.5k → €47.6k, conversion 54.8% → 55.7%, failed orders 46 → 52
- **project_state.md**: revenue figure updated to €47.6k

## 2026-04-08 — Active Grid B2B matching + Grid API hardening
- **Grid API hardening** (`grid_enrichment.py`):
  - Case-insensitive search workaround — `_ilike` was silently removed from Grid API; now tries 4 case variants (original, Title, UPPER, lower) with `_like`
  - Retry with backoff (2 retries, 1s/3s) on transient failures (timeout, 5xx)
  - GraphQL errors logged explicitly instead of silently swallowed
  - `health_check()` function verifies API reachability + filter syntax before the event
  - New admin endpoint: `GET /dashboard/grid-health`
- **Active Grid B2B matching** — Grid data now feeds into matching pipeline actively, not just passively through embedding text:
  - `embeddings.py`: Grid products + company type added to composite text (was only description + sector)
  - `matching.py`: 19-entry `GRID_SECTOR_TO_VERTICALS` map converts Grid sectors (e.g. "Custody and Wallets") into our vertical tags for COMPLEMENTARY_VERTICALS scoring
  - `matching.py`: `_grid_context()` feeds Grid-verified description, sector, type, and key products into GPT-4o candidate descriptions
  - `matching.py`: GPT-4o prompt instructs treating Grid data as most authoritative source; product-level supply/demand matching
  - `matching.py`: deterministic reranking merges Grid-derived verticals with explicit tags; extra +0.02 boost when both sides have verified Grid products
- **Sponsor Grid coverage**: 9/24 sponsors found in The Grid (Zircuit, CertiK, Taostats, BitGo, BitMEX, Paxos, ChangeNOW, Teroxx, Morph Network)

## 2026-04-08 — Sponsor Intelligence System brief
- Created `docs/sponsor-intelligence-brief.md` — team-facing document explaining the sponsor intelligence report system
- Covers: what sponsors get (personalised 20-target report), how it works technically, three pricing tiers (€5-10k / €15-25k / €50k+), what each team member needs to do, revenue projections (€40k-€325k), and timeline
- Key ask: generate 3 pilot reports for Zircuit, BitGo, CertiK so Victor can start pitching this week

## 2026-04-09 — Sponsor Intelligence Report Generator built
- Created `backend/scripts/sponsor_intelligence.py` — full pipeline for generating sponsor intelligence reports
- Pipeline: sponsor name → Grid API (reuses hardened `enrich_from_grid`) → composite text → OpenAI embedding → pgvector similarity vs all attendees → GPT-4o generates sponsor-specific explanations → branded HTML report
- Includes `--identify-team` flag to find sponsor team members already in the attendee pool
- 24 sponsors hardcoded from Google Sheet data; supports `--sponsor "Name"` for single runs
- Generated 3 pilot reports: Zircuit (2 HIGH, 3 MEDIUM), BitGo (2 HIGH, 3 MEDIUM), CertiK (1 HIGH, 3 MEDIUM)
- All 3 sponsors found in The Grid with verified sector/products data
- Reports saved as branded HTML with POT dark theme, relevance badges, conversation openers, deal potential

## 2026-04-09 — Sponsor Intelligence dashboard UI + confidence indicators
- Created `backend/app/services/sponsor_intelligence.py` — service layer using SQLAlchemy async (not raw asyncpg), reuses hardened `enrich_from_grid`, deterministic confidence scoring
- **Confidence scoring**: computed from data completeness (Grid verified, goals stated, intent tags, similarity, deal readiness) — NOT by GPT, prevents hallucinated confidence levels
- **GPT overstating mitigation**: prompt requires source tags ([GRID], [GOALS], [PROFILE], [AI-INFERRED]), forbids inventing details, forces "Goals not disclosed" when data is missing, requires conservative deal potential ratings, adds `key_evidence` and `caveats` fields
- **New endpoints**: `GET /dashboard/sponsors` (24 sponsors), `POST /dashboard/sponsor-report` (full pipeline with confidence)
- **Dashboard UI**: Sponsor Intelligence section with dropdown of 24 sponsors, Generate Report button (15-30s loading state), inline results showing summary stats, Grid verification status, avg confidence %, explanation cards with relevance badges, confidence dots, conversation openers, deal potential, caveats warnings, and key evidence tags
- Frontend builds clean, 0 TypeScript errors

## 2026-04-09 — Grid enrichment reliability fixes
- **Bug found**: "Proofoftalk" and "Proof of Talk" treated as different companies — Grid only matched one spelling. 32% Grid coverage (19/60 attendees)
- **Improved `_normalize_company_name()`**: handles connector words (of/and/the/for) with min-length guards, domain-stripped variants (.io/.ai/.co), more suffix splits. "Proofoftalk" → "Proof of talk" now resolves in Grid
- **Retry logic in enrichment.py**: Grid lookups now track `grid_attempted_at` timestamp; retries after 7 days if previous lookup failed (was: never retry)
- **New endpoint**: `POST /dashboard/re-enrich-grid` — bulk re-runs Grid enrichment for all attendees missing Grid data; admin dashboard button added ("Re-enrich Grid B2B")
- **Tested**: "Proofoftalk" → "Proof of Talk (Community & Events)" ✅ confirmed via Grid API

## 2026-04-14 — AI-inferred customer matching (Z's ICP vision)
- **New column** `attendees.inferred_customer_profile` (JSONB) — migration `c8d4e9a17f22`. Shape: `{offers, ideal_customers[{who, why, signal_keywords}], ideal_partners[...], anti_personas[]}`.
- **`infer_customer_profile()`** in `app/services/embeddings.py` — GPT-4o call that takes an attendee's name/title/company/goals/AI summary/vertical_tags/intent_tags + Grid verified data and infers who would realistically buy from, invest in, or partner with them. Prompt requires concrete personas (no generic "crypto companies") and 3-6 lowercase `signal_keywords` per persona that would appear in a matching attendee's profile text.
- **`process_attendee()`** in `matching.py` now runs inference automatically during enrichment — new registrations get ICP without manual backfill. Exceptions swallowed to `{}` so inference never blocks the pipeline.
- **Composite embedding text** (`build_composite_text`) now includes `Offers`, `Ideal Customers`, `Ideal Partners` lines with their signal keywords — similarity search now reflects "who would buy from this person" not just "what they look like."
- **Ranking prompt rewrite** — added target ICP block and explicit weight hierarchy: (1) EXPLICIT target_companies win automatically, (2) AI-INFERRED ICP preferred when no explicit targets — candidates get an "ICP MATCH SIGNAL" line listing which of the target's ICP keywords appear in their profile, (3) BASELINE similarity as floor. Two-way ICP fit (target matches candidate's ICP AND vice versa) flagged as deal-ready. Anti-competitor instruction added.
- **Deterministic rerank boosts** in `_deterministic_rerank`: +0.03 for 1 ICP keyword hit, +0.05 for ≥2 hits, +0.03 extra for two-way ICP fit — sits above Grid product boost (+0.02) and below complementary vertical boost (+0.04) per Z's weight hierarchy.
- **Company-similarity fallback** in `generate_matches_for_attendee` — if no matches clear `MIN_MATCH_SCORE`, surface up to 3 sector peers that share `vertical_tags` or Grid sector with score 0.60 and a labelled "Sector peer match" explanation. Prevents empty briefings for edge-case attendees.
- **Backfill script** `scripts/backfill_inferred_customers.py` — runs inference + re-embeds for all attendees missing ICP. Flags: `--force`, `--dry-run`, `--no-reembed`.
- **Regeneration script** `scripts/regenerate_matches.py` — one-shot runner for `run_matching_pipeline` (avoids the known HTTP timeout on `/dashboard/generate-all` for full batch runs).
- **Executed against Supabase production**: migration applied, backfill 60/60 success 0 failures, match regeneration produced **247 matches @ avg 0.720** (up from 0.704). Distribution: 210 complementary / 21 non_obvious / 16 deal_ready. Spot-check: Amara Okafor (Abu Dhabi SWF, $200M tokenised RWA mandate) now surfaces **Marcus Chen (VaultBridge custody infra) at 0.820 `deal_ready`** — the canonical case-study pairing is now the top match with a concrete ICP-driven explanation.
- **Still pending**: push to main + Railway auto-deploy (not yet done this session — local Supabase is already updated but Railway's code is still on the pre-ICP commit).

## 2026-04-15 — Ferd outreach sheet sync + ingest_extasy refactor
- **Ferd's ask**: Supabase → Google Sheet hourly sync so the outreach team stops cold-emailing investors who've already bought POT tickets. Master sheet `PoT26_Master_Email_Database_v3` (id `1L3SpraHSWDpTwEg2CiBQ3ytHT9mS5zvOljrtIABKw8Q`).
- **Approach**: Google Apps Script bound to the sheet + Supabase REST view. Rejected Edge Function (extra infra) and DB webhooks (overkill for hourly cadence). Keeps ops on Ferd's side, nothing new to deploy or monitor on ours.
- **Supabase side**: new read-only view `public.attendees_sync` exposing only `email, name, company, created_at, ticket_type, ticket_bought_at`; `grant select ... to anon`. Keeps the anon key's blast radius tiny. Applied via MCP migration `create_attendees_sync_view`.
- **Apps Script side**: writes to a new `POT Attendees` tab (mirror of the view) plus a `POT Sync Log` tab for run metadata. Deliberately does NOT write to `MERGED - All Investors` because Ferd's existing `mergeInvestorTabs()` drops-and-rebuilds that tab on every run — our data would get wiped. Script lives in the Sheet's editor; draft copy checked into `docs/integrations/sheets_sync/Code.gs`.
- **Trigger**: hourly time-based, installed manually via the Apps Script UI (Triggers → + Add Trigger → syncFromSupabase → Hour timer). The in-editor `installTrigger()` helper is also available.
- **Verified end-to-end**: 86 rows mirrored into `POT Attendees`, `POT Sync Log` recording each run.
- **.env typo fix**: renamed `SUPERBASE_ANON_KEY` → `SUPABASE_ANON_KEY` in `backend/.env`. Grep confirmed no backend code referenced the typoed name, safe to rename.
- **Bug discovered — `ingest_extasy.py` skip-if-exists**: only 3 of 70 Rhuna orders had `extasy_order_id` / `ticket_bought_at` / `extasy_ticket_code` populated in Supabase. Root cause: the ingest script's non-`--force` path skipped any row whose email already existed, so rows written by an earlier (pre-`184348d`) version of the script never got backfilled with the new metadata fields. `--force` would upsert the full record and wipe `enriched_profile`, `interests`, `ai_summary`, etc., so it wasn't a safe shortcut.
- **Refactor `upsert_to_supabase()` to insert-or-patch**:
  - New constant `EXTASY_PATCH_FIELDS = [extasy_order_id, extasy_ticket_code, extasy_ticket_name, phone_number, city, country_iso3, ticket_bought_at, ticket_type]` — fields where Rhuna is source of truth.
  - Existing row → GETs current values, builds a diff, PATCHes only changed fields via `PATCH /rest/v1/attendees?email=eq.{email}`. Never touches `interests`, `goals`, `seeking`, `enriched_profile`, `ai_summary`, `embedding`, `linkedin_url`, `twitter_handle`, `company`, `title`.
  - New row → POST full record (unchanged behaviour).
  - No-op PATCHes (where existing already matches desired) skipped entirely — no API call, counted as `NOOP`.
  - `--force` repurposed: now means "also PATCH `enriched_profile` on existing rows" — disaster recovery only, not the default.
  - Per-row trace shows `INSERT` / `PATCH [fields...]` / `NOOP` so dry-runs are readable.
  - The script is now safe to schedule (cron / Railway job) — each run is idempotent and self-heals drift from Rhuna.
- **Backfill executed**: dry-run showed `0 inserted, 67 patched, 3 unchanged, 0 errors / 70 total` — picked up Lamar Ellis as the only row needing `ticket_type` corrected alongside the metadata backfill. Real run matched dry-run exactly. Post-run Supabase state: `extasy_order_id`, `ticket_bought_at`, `extasy_ticket_code` all moved from 3 → **70** populated rows. Verified via spot-check on 5 rows that `enriched_profile`, `ai_summary`, `embedding`, and `interests` were all preserved — `shaunkudzi@gmail.com` (not in Rhuna, correctly skipped) still had all 9 interests intact, proving the diff-only PATCH doesn't touch non-Extasy fields.
- **Known 1000 Minds nomination gap (not yet shipped)**: while inspecting the Supabase schema, confirmed that the 1000 Minds app shares this Supabase project but uses a separate `nominations` table (219 rows). These nominees are not in `attendees`, so today's sheet sync doesn't protect against the outreach team double-contacting them. Proposed a second `POT Nominees` tab using the same hourly pattern — pending Ferd's decision on whether to add it.
- **Files touched**: `backend/scripts/ingest_extasy.py` (refactor), `backend/.env` (typo fix), `docs/integrations/sheets_sync/Code.gs` (new, repo copy of deployed script), `docs/integrations/sheets_sync/README.md` (new).

## 2026-04-16 — Ferd v2: consolidated POT Attendees + In Funnel flag on all feeder tabs
- **Ferd's feedback**: team works from individual feeder tabs (COLD - T1 VCs, Startups, etc.), not from MERGED. Wanted the `In Funnel` flag on every outreach tab, with TRUE/FALSE and green fill on TRUE, using a formula so new rows get flagged automatically.
- **Supabase side**: new read-only view `public.nominations_sync` exposing `nominee_email, nominee_name, nominee_company, nominee_title, nominator_name, nominator_email, status, nominee_confirmed, created_at`; `grant select ... to anon`. Applied via MCP migration `create_nominations_sync_view`. 224 nominees visible.
- **POT Attendees consolidated**: single tab now combines attendees (86, Source=TICKET) + nominees (224+, Source=NOMINEE) into one ~310-row source of truth. New columns: `Source`, `Confirmed`. Replaced the previous separate `syncAttendees` + `syncNominations` with a single `syncPotAttendees` function.
- **ARRAYFORMULA-based `In Funnel` column**: `addFunnelFormulas()` iterates all non-excluded tabs, finds `Contact Email` by header scan, writes `=ARRAYFORMULA(IF(COUNTIF('POT Attendees'!A:A, emailCol)>0, TRUE, FALSE))` into a new `In Funnel` column. The formula auto-flags new rows instantly — no wait for the daily sync. Conditional formatting rule sets green background on TRUE cells.
- **Tab discovery is automatic**: iterates all tabs, skips `SKIP_TABS` set (Dashboard, POT Attendees, POT Nominees, POT Sync Log, MERGED, EXCLUDE tabs, NEW). Any future tab with a `Contact Email` header gets the flag automatically.
- **Bug fix — ARRAYFORMULA blocked by stale static values**: the previous `addFunnelFlag()` run wrote static FALSE values to every cell. The ARRAYFORMULA couldn't expand because cells below row 2 weren't empty. Fix: `clearContent()` on the column before setting the formula.
- **Trigger changed from hourly to daily**: `atHour(23).everyDays(1)` — runs at ~11 PM to reduce noise. Old `syncFromSupabase` trigger deleted.
- **Tab rename**: Ferd renamed `WARM - Ferdi Investors` → `Close network of Investors` and restored its data from version history.
- **Verified end-to-end**: `In Funnel` column visible on `Close network of Investors`, `COLD - T1 VCs`, `COLD - T2 T3 VCs`, `COLD - Startups`, `COLD - Family Offices LPs`, `COLD - Accelerators`. Green TRUE cells confirmed for matching emails (e.g. `julien@stake.capital` = ticket holder, `simon@moonrockcapital.io` = nominee). Overlap is small — a handful across ~2500+ cold contacts.
- **Files touched**: `docs/integrations/sheets_sync/Code.gs` (rewritten — consolidated sync + ARRAYFORMULA approach).

## 2026-04-20–21 — Category column, Attendees page fixes, AI guardrails, live sponsors, enrichment audit
- **Ferd's Category request**: added AI-inferred `Category` column to POT Attendees (Investor/Exchange/Regulator/Startup/Infrastructure/etc.). SQL CASE expression in `attendees_sync` view uses intent_tags + `inferred_customer_profile.offers` text matching. ~80% accurate, Ferd accepted as starting point.
- **Nominations view updated**: `nominations_sync` now includes `nominee_vertical` and `nominee_seniority` for category coverage on nominees.
- **Attendees page fixes (3 bugs)**:
  - Search: removed `ai_summary` from search fields — "proof of talk" was matching every attendee's summary. Replaced with email search.
  - Overflow: AI summary clamped to `line-clamp-2`, card has `overflow-hidden`, Brain icon uses `shrink-0`.
  - Sponsor filter removed: 0 sponsors in DB (sponsors are CRM relationships, not attendees). Removed from `TICKET_TYPES`.
- **Live sponsor data**: `sponsor_intelligence.py` now reads from CEO Dashboard Supabase (`emsofswnzqnepekmiwwp/dashboard_snapshots`) via REST API instead of hardcoded 24-sponsor list. Returns 37 live sponsors from CRM. Falls back to hardcoded list if env vars missing. New env vars: `CEO_DASH_SUPABASE_URL`, `CEO_DASH_SUPABASE_ANON_KEY`.
- **Admin password reset**: both `admin@pot.demo` and `shaun@proofoftalk.io` passwords reset via direct DB update (bcrypt hash). Old passwords were failing.
- **Admin attendee profile removed**: unlinked `admin@pot.demo` from attendees table and deleted the attendee row — admin is not a real attendee, shouldn't have matches.
- **AI Concierge anti-hallucination guardrails** (`concierge.py`):
  - 7 accuracy rules in system prompt: don't invent facts, tag claims with sources, flag sparse data honestly.
  - Attendee context labels each field `[VERIFIED]` vs `[AI-INFERRED]`.
  - Data quality score per attendee (SPARSE/PARTIAL/GOOD) based on real field coverage.
  - AI summary suppressed for SPARSE profiles (completeness ≤1) — model can't see fabricated text.
  - Smoke tested: sparse profiles now say "goals aren't detailed" instead of fabricating.
- **Upstream enrichment guardrails** (`embeddings.py` + `enrich_and_embed.py`):
  - `generate_ai_summary()` checks data completeness before calling GPT. Sparse profiles (no interests, no goals, no meaningful enrichment) get a factual stub — no GPT call, no hallucination.
  - Only counts meaningful enrichment keys (linkedin, grid, twitter, crunchbase, company_description) — not Extasy ticket metadata.
  - GPT prompt has explicit anti-fabrication rules matching the sponsor intelligence pattern.
  - Both the service version and batch script version updated.
  - All 96 AI summaries regenerated: 45 stubs, 51 GPT with guardrails, 0 errors.
- **LinkedIn enrichment audit**: Voyager `FullProfileWithEntities-86` endpoint returns 410 (deprecated). Proxycurl API sunset (returns 410, team moved to NinjaPear at $49/mo — too expensive for 96 profiles). Fresh cookies obtained but LinkedIn changed internal API structure — `identity/dash/profiles` no longer called by frontend. LinkedIn enrichment is effectively dead. Grid B2B + website scraping remain as primary enrichment sources.
- **Files touched**: `backend/app/services/concierge.py`, `backend/app/services/embeddings.py`, `backend/app/services/sponsor_intelligence.py`, `backend/app/api/routes/dashboard.py`, `backend/scripts/enrich_and_embed.py`, `frontend/src/pages/Attendees.tsx`, `docs/integrations/sheets_sync/Code.gs`.

## 2026-04-14 (cont.) — ICP deployed + Runa sync + seed removal + infrastructure cleanup
- **DATABASE_URL fixed**: `.env` from old machine still pointed at decommissioned AWS RDS (`pot-matchmaker.c16ym02woedf.eu-west-1.rds.amazonaws.com`). All SQLAlchemy operations (alembic, backfill, regen) had been running against RDS, not Supabase production. Fixed to `postgresql+asyncpg://postgres:***@db.mkcememoueziibbpqhfk.supabase.co:5432/postgres`. Supabase confirmed at 92 attendees vs RDS frozen at 60.
- **ICP re-run on Supabase**: alembic migration applied to Supabase (was only on RDS), ICP backfill 92/92 success, match regeneration 387 matches @ avg 0.727.
- **Runa/Extasy sync**: `ingest_extasy.py` enum fix — Supabase UPPERCASE tickettype enum (`VIP`/`DELEGATE`) vs script sending lowercase → inserts silently failed. Fixed `TICKET_TYPE_MAP` + default + `tier_order` to UPPERCASE. 2 new attendees ingested: Bruno Calabretta (VIP), tony mclaughlin (General).
- **Seed profile removal**: deleted 5 case-study seeds (Amara Okafor, Marcus Chen, Elena Vasquez, James Whitfield, Sophie Bergmann) + 1 test user (test-integration@example.com). 40 matches dropped, 6 attendees removed. 88 → 82 attendees (later rose with new syncs).
- **Duplicate profile merges (round 1)**: Victor Blas (2 records: speaker.proofoftalk.io + xventures.de → kept xventures.de), Shaun (2 records: thenerdsint@gmail.com + shaun@proofoftalk.io → kept proofoftalk.io). 4 collision matches dropped, 6 reassigned, 1 user row removed.
- **AWS RDS stopped**: took final snapshot `pot-matchmaker-preretire-20260415-0757`, stopped instance via boto3. Saves ~€12/mo compute. Note: AWS auto-restarts stopped instances after 7 days — should delete with final snapshot if not needed.
- **Netlify auto-deploy repaired**: GitHub App installed at org level, but site `pot-matchmaker` was still bound to dead OAuth token. Fixed by: Manage repository → Link to a different repository → re-select `Kanyuchi/Proof_Of_Talk_CD`. Verified with empty commit `7fd610b` → `Production: main@7fd610b Published ✓`. Frontend rebuild + deploy via `npx netlify deploy --prod --dir=frontend/dist` done earlier as stopgap.

## 2026-04-15 — Background jobs, sponsor exclusion, Grid hardening
- **Background job system** (`app/services/jobs.py`): in-memory job tracker for long-running admin ops. `submit()` → asyncio.create_task, `get()` for status polling, 1h TTL auto-cleanup. Prevents Railway's 30s HTTP edge timeout (504s).
- **Endpoints converted**: `POST /dashboard/re-enrich-grid` and `POST /dashboard/sponsor-report` now return `202 {job_id}` immediately, run actual work via asyncio.create_task with fresh DB session. Added `GET /dashboard/jobs/{job_id}` status polling + `GET /dashboard/jobs` listing.
- **Frontend polling**: `reEnrichGrid()` + `generateSponsorReport()` in `client.ts` now submit → poll `/dashboard/jobs/{id}` every 2.5-3s → surface result/error. 10m timeout for Grid, 5m for sponsor.
- **Sponsor intelligence internal exclusion**: `_find_relevant_attendees()` in `sponsor_intelligence.py` now filters out internal staff by company patterns (`proof of talk`, `xventures`, etc.) + email root domain (`@proofoftalk.io`, `@xventures.de`). `@speaker.proofoftalk.io` stays — legitimate external speakers. Previously sponsor reports surfaced Nupur/Jessica/Victor as HIGH-relevance targets.
- **JSONB mutation tracking fix**: `EnrichmentService.enrich_attendee()` returned the same dict reference from `attendee.enriched_profile`, so reassignment was a no-op for SQLAlchemy. Fix: `enriched = dict(attendee.enriched_profile or {})` returns a fresh copy. Added `flag_modified(attendee, 'enriched_profile')` at all call sites. Previously Grid re-enrichment silently dropped all mutations.
- **Grid matcher false-positive stopword filter**: `_best_match()` rewired to strict 3-stage policy: (1) exact name, (2) prefix, (3) 100% non-stopword token overlap. Business stopwords (`ventures`, `capital`, `labs`, `group`, `foundation`, etc.) excluded from matching tokens. Killed the "if single result, accept" fallback that let `Atos→Satoshigallery` and `X Ventures→MarketX Ventures` through. 10/10 unit tests pass.
- **Grid null field guards**: `_extract_urls`, `_extract_socials`, `_extract_media` crashed with `NoneType.get()` when Grid returned explicit JSON null for typed fields (e.g. Vancelian's `urlType: null`). Fixed all three to `(x.get(key) or {}).get(...)`.
- **Grid status filter relaxed**: PROFILE_QUERY expanded from `profileStatus = "active"` to `{_in: ["active", "announced"]}`. Recovered Ubyx (status=announced) and Vancelian (was crashing). Wello (status=closed) correctly excluded.
- **Duplicate profile merges (round 2)**: Kathryn Dodds (speaker + gunnercooke delegate → kept delegate), Pavan Kaur (speaker + rulespark delegate → kept delegate). 4 collision matches dropped.
- **False positive Grid data cleared**: removed bad Grid entries for Christophe Visentin (Atos→Satoshigallery), Hedeyeh Taheri (Atos→Satoshigallery), Victor Blas (X Ventures→MarketX Ventures), Admin (POT→Spot On Chain).
- **Grid coverage audit**: probed all 34 corporate email domains via Grid URL search — 0 additional matches found. Confirmed 23/85 (27%) is the real ceiling. CSV exports at `exports/non_grid_attendees.csv` and `exports/grid_url_coverage_full.csv`.
- **Final state after all fixes**: 85 attendees, 23 Grid verified (27%), 234 matches @ avg 0.713.

## 2026-04-17 — All emails disabled + revenue dedup removed
- **All outbound emails disabled**: added `return  # BLOCKED: platform not yet open to attendees` to `send_password_reset_email`, `send_mutual_match_email`, `send_meeting_confirmation_email` in `email.py`. Match intro was already disabled since `97d8fa0`. Triggered by Pouneh Bligaard (Dragonfly Asset Management) contacting via LinkedIn — she has a Rhuna ticket but no user account, password reset email never arrived because there's no user to reset, but mutual-match/meeting emails would have gone out if someone interacted with her matches. Zero emails will send until the `return` lines are removed.
- **Revenue dedup removed**: our `(email, ticket_name, amount)` dedup was dropping Tommi Vuorenmaa's legitimate second Startup Pass purchase (€599), creating a €600 gap between our €63,529 and Rhuna's €64,129. Rhuna is the ticketing source of truth and handles order-level dedup. Removed our custom dedup — revenue now matches Rhuna exactly.
- **Dashboard investigation**: confirmed CEO dash (pot26-ceo) reads from a manually-exported Google Sheet ("RAW Tickets"), not live Extasy API. The €52k vs €57k+ gap from earlier sessions was stale data + manual reclassification (4 "Media" tickets that don't exist in Extasy). Also confirmed 44 of 102 "paid" orders are €0 comps/vouchers — only ~58 are revenue-generating. CEO dash source = Google Sheet (curated), matchmaker dash source = Extasy API (live).

## 2026-04-19 — Meeting Prep Brief (Phase 4) + Contact Export + Post-Event email stubs (Phase 5-6)
- **Meeting Prep Brief page** (`frontend/src/pages/Briefing.tsx`) — new route `/m/:token/briefing` accessible via magic link, no login. Shows personalised meeting prep for each attendee: header with name/role/AI summary/stats, per-match cards with match type badge, score, "Why You Should Meet" explanation, talking points (from shared_context.action_items), shared context sectors/synergies, Grid-verified company intelligence, social links, scheduled meeting details. Print/PDF via `window.print()` with dedicated print CSS (@page A4, white bg, hides nav). "View Meeting Prep Brief" button added to MagicMatches page.
- **Contact Export** — "Export Contacts" button on Briefing page generates CSV (Name, Title, Company, Match Type, Score, LinkedIn, Twitter, Website, explanation, talking points). Frontend-only using Blob API, no backend call needed. Downloads as `POT2026_Contacts_{name}.csv`.
- **Post-event email stubs** in `email.py`:
  - `send_morning_schedule_email()` (Phase 5) — "You have N meetings today" for each conference day at 07:00
  - `send_post_event_wrapup_email()` (Phase 6) — D+1 summary: stats, top connections, LinkedIn CTAs, briefing link
  - `send_followup_nudge_email()` (Phase 6) — D+7 nudge: "Deals close in the first week" + reconnect prompts
  - All 3 have `return` at top (blocked like all other emails). Full HTML templates ready to add when emails re-enabled.
- **Matchmaking UX integration brief** for Zohair — `docs/matchmaking-ux-integration.md` + Word doc at `docs/Matchmaking_UX_Integration_Brief.docx`. Covers the full 6-phase attendee timeline (Instant → First Matches → Warm-Up → Final Briefing → At-Event → Post-Event), what's built vs what's needed, and the critical unlock (Rhuna → magic link → matches in 24h).
- **All email functions now stubbed** across the full lifecycle: 7 email types (match intro, password reset, mutual match, meeting confirmation, morning schedule, D+1 wrap-up, D+7 nudge), all blocked with `return`, all ready to enable with one line removal each.

## 2026-04-23 — LinkedIn enrichment restored via linkedin-api library

- **`linkedin-api` integration** — replaced dead Proxycurl + manual Voyager cookie approach with the free `linkedin-api` Python library (v2.3.1, wraps Voyager internally, authenticates with email+password)
- **`enrichment.py`**: new `_enrich_linkedin_api()` method as primary LinkedIn source; lazy singleton client with auto-auth; runs in thread executor (library is sync, service is async); 3s rate limit between requests; falls back to manual Voyager cookies if `linkedin-api` auth fails
- **`_verify_linkedin_identifier()`**: updated to try `linkedin-api` first for URL resolution, Voyager cookies as fallback
- **`enrich_and_embed.py`**: standalone script now includes LinkedIn as Layer 0 before website scraping; `--skip-linkedin` flag added; fetches `linkedin_url` from Supabase; auto-populates `title` from LinkedIn headline when missing
- **Config**: `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` env vars added to `config.py` and `.env.example`; `PROXYCURL_API_KEY` marked as defunct
- **CLAUDE.md**: LinkedIn enrichment status updated from "non-functional" to "functional via linkedin-api"
- **Voyager dash endpoint fix**: `linkedin-api` library's `get_profile()` returns 410 (old endpoint deprecated); rewrote `_enrich_linkedin_api()` to use library only for auth, then call the working `dash/profiles` endpoint directly with the session cookies
- **Playwright scraper run**: scraped 21/25 LinkedIn profiles successfully (4 private/blocked); delay increased to 10s; 7 wrong-person enrichments (bad URLs like `/in/robin-s`, `/in/mark`) cleaned up and URLs cleared from Supabase
- **Full re-enrichment**: `enrich_and_embed.py --force --skip-linkedin` regenerated all 115 AI summaries, intent tags, and embeddings incorporating the new LinkedIn data

## 2026-04-24 — LinkedIn discovery mode + Grid URL-fallback + full enrichment

- **Playwright LinkedIn discovery mode**: rewrote `discover_linkedin_url()` to use LinkedIn's search UI (`/search/results/people/?keywords=...`) instead of naive slug guessing; discovers URLs from the first matching search result that contains both first + last name. Ran across 128 attendees (73 with URLs, 98 without) — found 39 new URLs, enriched 70 total LinkedIn profiles (up from 14). LinkedIn URL coverage jumped from 15% → 63%, LinkedIn data coverage from 12% → 60%.
- **Grid domain audit** (`backend/scripts/grid_domain_audit.py`): new standalone audit tool that maps every non-generic email domain → Grid slug using two strategies: (1) URL-contains search (Grid profile's URL list includes the domain), (2) alnum-normalized slug equality (e.g. `sundaebar.ai` == `sundae_bar` after normalizing). Tightened slug strategy: dropped `slug_tokens` (too loose, caused `castlelabs.io` → `the_old_castle_defence`), dropped TLD-suffix stripping (caused `aztecai.ai` → `aztec`, `babslabs.io` → `babs`), added `PLATFORM_DOMAINS` filter (google/twitter/linkedin etc. skip URL-contains to avoid matching unrelated profiles that link to them). Result: 22/72 domains match Grid cleanly, 0 false positives. CSV at `backend/exports/grid_domain_coverage.csv` (gitignored).
- **Grid URL-fallback in `grid_enrichment.py`**: `enrich_from_grid()` now accepts an `email_domain` arg and falls back to URL-contains search when name search misses. Picks up name-mismatch cases like `GenVentures` → `Generative Ventures` that Grid has but our name-based search couldn't match. Added `URL_SEARCH_QUERY`, `_PLATFORM_DOMAINS` set, and `_search_grid_by_url()` helper.
- **Grid enrichment added to `enrich_and_embed.py`**: previously the standalone script skipped Grid entirely (only the FastAPI service did it). Added Grid as Layer 1.5 (between website scrape and AI summary). Grid data (description, sector, products) now feeds into the composite embedding text via a new `Verified (Grid): ...` line in `build_composite_text()`.
- **Full re-enrichment**: `enrich_and_embed.py --force --skip-linkedin` processed all 116 attendees end-to-end. Final coverage: LinkedIn URL 73/116 (63%), LinkedIn data 70/116 (60%, all Playwright-scraped), Grid 36/116 (31%, up from 23%), website 67/116 (58%), AI summary + embedding 116/116 (100%). All regenerated with the richer data context.
- **Idempotency**: confirmed existing `enriched_profile.{linkedin,grid}_enriched_at` timestamps already serve as "already done" markers — no new columns needed. The pipeline skips cached data unless `--force`, and Grid tracks `grid_attempted_at` separately so misses aren't retried for 7 days.

## 2026-04-24 — Rhuna ticket audit (free vs paid breakdown for Ferd)

- **Trigger**: Ferd asked what `Ticket Type: DELEGATE` means in the `POT Attendees` tab, and whether all the investors on that tab were free — they're a mix of paid and comped General Passes, all mapped to DELEGATE.
- **New `backend/scripts/rhuna_ticket_audit.py`**: read-only audit that fetches live Extasy orders (same endpoint as `dashboard.py:528` — `/operations/reports/orders/{EVENT_ID}`), joins to Supabase `ticket_type` enum, classifies each PAID/REDEEMED order as FREE or PAID, flags voucher-comped rows, and exports `backend/exports/rhuna_ticket_audit.csv` (gitignored).
- **Why live API not Supabase**: our ingest (`ingest_extasy.py:160`) stores `paid_amount = order.paymentsAmount`, but Extasy returns price in `fullPrice` for many rows — Supabase's `enriched_profile.raw_order.paid_amount` is €0 across the board and unreliable. The dashboard already uses `paymentsAmount OR fullPrice` fallback (`dashboard.py:569`); the audit script does the same.
- **Results (2026-04-24 snapshot)**: 230 total orders → 125 valid (PAID+REDEEMED non-test) → **76 FREE (€0), 49 PAID (€67,497.64 total)**. FREE breakdown: 46 DELEGATE-tier General/Startup passes (voucher codes like `NAMESURNAME1000` = 1000 Minds investor attribution), 23 VIP, rest Press/other. Ticket-name mix: General Pass 61, Press Pass 37, VIP Pass 16, Startup Pass 6, Investor Pass 3, VIP Black 2.
- **Ferd-relevant insight**: the 25 investors in his screenshot are a mix — some paid €839–€1199 for General Pass (David Chapman, Kapil Ramgirwar, Matjaz Stamulak, Sutton Bossie, Patrick Jahnke, pouneh bligaard, etc.), others are comped via unique `NAME1000` vouchers (Martin Quensel, Olga Antonova, Stuart MacDonald, Laura Inamedinova, etc.). The DELEGATE label alone can't distinguish them — only the live Extasy API's `paymentsAmount` / `voucherCode` can. Audit CSV is the source of truth to answer Ferd.
- **Not shipped**: did not extend the `attendees_sync` Supabase view or `POT Attendees` Apps Script to surface `extasy_ticket_name` / `is_comped` columns in Ferd's sheet. Deferred until Ferd explicitly asks; the audit CSV answers the current question.

## 2026-04-24 (afternoon) — LinkedIn discovery v2 + validator + final clean enrichment

- **Improved LinkedIn discovery** (`linkedin_scrape.py`): two-pass search (name+company → name-only fallback for email-derived "company" names like Catierf), hyphen+accent normalization (Catie Romero-Finger, Aurélien, Monika Górska), wider DOM selector (`[data-chameleon-result-urn]`, entity divs). New `--only-missing` flag retries just the failed discoveries. Found 37 of 43 missing profiles (88% hit rate) including Catie Romero-Finger.
- **LinkedIn validator** (`backend/scripts/validate_linkedin.py`): checks scraped slug + headline against attendee's registered name/company. Heuristics: accept abbreviations (`abhiguj` for Abhilash Gujar), accept initial+last patterns (`jbouteloup`, `pjahnke`, `o-antonova`), hard-fail on different first-name token in slug (Jaime → Fernando), escape hatch when headline mentions attendee's last name or company. Of 107 LinkedIn-enriched: 98 OK, 4 suspicious, 5 auto-cleaned (Aditya/d5ter, Welcome to Proof of Talk placeholder, Richard Holmes/mineaction, Sebastian Felipe name-swap, Jaime Pena/Fernando).
- **Manual cleanup**: 3 wrong-person matches the validator missed because slug surnames matched as substrings: Razvan Paun → razvanalexpaun (Amazon Alexa, not Dragonfly), Aurélien Cambron → cambronne (different surname), Xavier Gomez → xaviertenaqueralt (different surname).
- **Final re-enrichment**: full 116-attendee batch with `--force --skip-linkedin` regenerated all AI summaries, intent tags, embeddings using cleaned data. Final coverage: **87% LinkedIn URL (101/116), 84% LinkedIn data (98/116), 31% Grid (36/116), 58% website, 100% AI summary + embedding**.

## 2026-04-27 / 2026-04-28 — Ticket-holder export for Karl + critical extasy_sync bugs uncovered & fixed

**Triggered by Karl asking for a CSV of ticket holders with company + position.** Building the export surfaced a chain of three production bugs that explain why Supabase ticket-holder data has been silently drifting from Rhuna for weeks.

### Karl's CSV
- **New `backend/scripts/export_ticket_holders.py`** — pulls everyone with `extasy_order_id IS NOT NULL` from Supabase; falls back to `enriched_profile.linkedin.headline` when the registration `title` is empty (since most Rhuna ticket holders never filled in a job title). Output: `backend/exports/ticket_holders_company_position.csv` (gitignored). Final coverage with all fixes applied: **107 ticket holders, 76% company, 79% position, 86% LinkedIn URL**.
- LinkedIn scrape backfill: ran `scripts/linkedin_scrape.py` against the 59 holders who had a URL but no title — 97 enriched, headlines populated under `enriched_profile.linkedin.headline`. The export script now uses headline as the position fallback (lifts position coverage from 15% → 79%).

### Bug #1 — Silent skip on existing rows (`extasy_sync.py:171-172`)
- Previous behavior: when a ticket order's email matched an existing attendee row (e.g. someone already in attendees via the speaker/nomination path), the sync only updated the row if it was a tier upgrade. Otherwise it incremented `skipped` and **never wrote the `extasy_order_id` back**.
- Effect: ~26 paying attendees (Francesco Castle, Joanna Kelly, William De'Ath, Jordan Leech, Devon Euring, Javier Bastardo, Lukasz Dec, etc.) had profiles + matches but their ticket-holder linkage was invisible.

### Bug #2 — ORM model missing two columns
- `attendees` table has top-level `extasy_order_id VARCHAR` and `country_iso3 VARCHAR(3)` columns (added via Alembic at some point), but **the SQLAlchemy `Attendee` ORM class never declared them**. Setting `attendee.extasy_order_id = "..."` did nothing — SQLAlchemy ignored the attribute on UPDATE/INSERT.
- Effect: even when `extasy_sync` *tried* to backfill these fields, nothing persisted. This had been silently broken since the columns were added.
- **Fix**: added both columns to `backend/app/models/attendee.py` as `Mapped[str | None]` with `extasy_order_id` indexed.

### Bug #3 — Session poisoning in `sync_extasy_to_db()` (the catastrophic one)
- Production scheduler logs (`railway logs --json --lines 5000`) showed the 02:00 UTC daily Extasy sync **firing every night but inserting zero rows**. First order each night that triggered an `IntegrityError: duplicate key value violates unique constraint "attendees_email_key"` poisoned the SQLAlchemy session; the per-iteration `try/except` logged the error but didn't `await db.rollback()`, so every subsequent flush() failed with `"This Session's transaction has been rolled back due to a previous exception"`. Final `await db.commit()` ran against a poisoned session → nothing persisted.
- Logs from 2026-04-27 02:00 UTC showed 99 cascading errors and **zero `pipeline complete` log entries** — the function never returned successfully.
- **Fix**: wrapped each row in `async with db.begin_nested()` (Postgres SAVEPOINT). One bad row now rolls back its own savepoint without affecting siblings. Added separate `IntegrityError` handler (warning) vs general `Exception` handler (error). Added defensive `await db.rollback()` if the final commit ever fails.
- Why the IntegrityError happens at all (Bug #2 underneath): when the ORM didn't know about `extasy_order_id`, every nightly sync would try to INSERT (since SELECT-by-email might miss whitespace-padded versions inserted by other paths), hit a unique-violation on the email, poison, cascade.

### Verification
- Local `sync_and_enrich()` after all three fixes: `inserted: 0, backfilled: 26, upgraded: 0, skipped: 81, errors: 0`. Supabase HEAD count: **107 attendees with `extasy_order_id` populated** (was 81). Lukasz, Francesco verified linked.
- Remaining gap: 132 valid Extasy orders → 107 unique buyer emails = 25 multi-ticket / reassigned-ticket buyers. Those secondary attendees aren't in `attendees` because the model is one-row-per-buyer-email. Documented as a known limitation, not currently fixed.

### Files touched
- `backend/app/models/attendee.py` — added `extasy_order_id` + `country_iso3` to ORM
- `backend/app/services/extasy_sync.py` — savepoint per row, always-backfill on existing, separate IntegrityError handler, `backfilled` counter added to stats
- `backend/scripts/export_ticket_holders.py` — new
- `backend/scripts/rhuna_full_export.py` — new (already-present helper used during diagnosis)
- `backend/scripts/rhuna_ticket_audit.py` — already present
- `backend/exports/ticket_holders_company_position.csv` — gitignored output

### Operational findings (handover-critical)
- **Daily 02:00 UTC scheduler IS running** in Railway (`railway logs` confirmed timestamps). It just produced zero useful work since the bugs were introduced. Now that fixes are in, it should write properly.
- **Dashboard at meet.proofoftalk.io always *looked* current** because the dashboard reads live from Extasy API on every page load — masking the underlying Supabase drift completely. Add a `last_extasy_sync_at` indicator so this kind of silent failure is detectable next time.
- **Railway CLI installed locally** via `brew install railway`, project linked to `observant-achievement` (the random Railway codename for POT). Useful for future log diagnostics: `cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD && railway logs --json --lines 5000`.

### Not yet done (carried into whats_next.md)
- Alembic migration mirroring the ORM column additions (DB and model are aligned because the columns were added by hand at some point; a fresh DB stand-up would diverge without a migration).
- Commit + push the two-file fix.
- Verify on Railway after deploy that the scheduler now logs `pipeline complete`.
- Change `main.py:49` from `CronTrigger(hour=2, minute=0)` to `IntervalTrigger(hours=5)` per Karl's request — only after fixed sync confirmed working in production.
- Add `last_extasy_sync_at` timestamp to admin dashboard for drift visibility.

## 2026-04-29 17:40 — Match dossier mockup + Grid coverage backfill

### Match dossier mockup
- `docs/mockups/match-dossier.html` — single-file Louvre-themed dossier presenting one match (Zohair ↔ Victor, deal_ready 0.78). Cream paper, gilt rules, Playfair + Poppins, no code change. Inspiration: proofoftalk.io (fetch was 403-blocked by Cloudflare; used in-repo brand tokens from `frontend/src/index.css` instead).

### Grid coverage audit + backfill
- Re-ran `backend/scripts/grid_domain_audit.py` (was 5 days stale — manual one-off, not scheduled).
  - 24 Apr → 29 Apr: 72→83 domains, 88→100 attendees on company emails, 21→24 Grid matches. Coverage rate flat at 32% of company-email attendees (~9 attendees on personal/gmail-style domains are excluded by design).
  - Three new Grid profiles surfaced by URL-contains search that the original name-based enrichment missed: `bundesblock.de` → Blockchain Bundesverband, `digital-euro-association.de` → Digital Euro Association, `stablecoinstandard.com` → Stablecoin Standard.
- New script `backend/scripts/grid_backfill_domains.py` — surgical, idempotent backfill for specific email domains. Reuses `enrich_from_grid()` so the resulting `enriched_profile.grid` shape is identical to the main pipeline.
  - Dry-run, then live run: 3/3 attendees patched (Daniela Boback, Manuel Müller, Christian Walker), all sector "Industry Bodies & Trade Associations". Verified by direct Supabase query.
- Refreshed `backend/exports/grid_domain_coverage.csv` (24 → 29 April).

### Root cause of staleness
- `grid_domain_audit.py` is a manual command. There is no scheduler invoking it. Will be addressed next.

### Files touched
- `docs/mockups/match-dossier.html` — new
- `backend/scripts/grid_backfill_domains.py` — new
- `backend/exports/grid_domain_coverage.csv` — refreshed
## 2026-04-29 18:50 — Daily Grid audit wired into Railway scheduler

### What
- New `grid_audit_runs` table — one row per daily audit, with totals + new-matches list + unmatched-domains list. Migration `e1f2d4a36789`.
- New service `app/services/grid_audit.py` — runs the audit using the same URL-search primitive as `enrich_from_grid()`, persists a row via SQLAlchemy, exposes `last_audit()` for the admin dashboard.
- New scheduler job in `app/main.py`: 02:30 UTC daily, after Extasy (02:00) and speakers (02:15). Logs structured summary on each run.

### Why
- `scripts/grid_domain_audit.py` was a manual one-off. Numbers went stale (5 days). Wiring into the Railway scheduler that already runs the daily Extasy + speakers sync gives us a daily fresh row, addressable from the dashboard.

### Verified
- `alembic upgrade head` applied cleanly.
- End-to-end smoke test via `run_and_persist()`: 83 domains, 24 matched, 32/100 attendees covered, duration 74.56s, row persisted (id 733a186b…), `last_audit()` readback works.
- `new_matches=0` — confirms today's earlier backfill landed cleanly across the 3 domains discovered in the previous run.

### Files touched
- `backend/alembic/versions/e1f2d4a36789_add_grid_audit_runs.py` — new
- `backend/alembic/env.py` — register GridAuditRun model
- `backend/app/models/grid_audit_run.py` — new
- `backend/app/services/grid_audit.py` — new
- `backend/app/main.py` — third scheduler job

### Not yet
- Admin dashboard surface for the audit history. The data is queryable via `last_audit()` but no UI yet — defer.
- Task 3: triage the 59 unmatched domains.

## 2026-04-29 19:05 — Triage of unmatched audit domains

- New `backend/scripts/grid_unmatched_triage.py` — pulls the latest `grid_audit_runs.unmatched_domains` list, fetches each domain's attendee enrichment from Supabase, classifies via keyword + vertical-tag heuristics into HIGH / MED / LOW.
- Latest run (59 unmatched): HIGH=37, MED=15, LOW=7.
- Outputs: `backend/exports/grid_unmatched_triage.md` (human-readable, send to Grid team after manual scrub) + `.csv` (batch-friendly).
- Known false positives in HIGH (manual scrub before sending): `vanlanschotkempen.com` (bank, "bitcoin" keyword caught a single attendee bio), `undp.org` (UN agency), `drofa-ra.co.uk` (PR agency for crypto clients), `arabbank.ch` (traditional bank).
- Genuinely Grid-worthy at first glance: castlelabs.io, mpmlabs.xyz, eternax.ai, flight3.xyz, youhodler.com, kula.com, theqrl.org, dragonflydigitalassets.fund, sakurafinance.com, ~25 others.

## 2026-04-29 19:55 — Closed Supabase RLS advisor warning

### What
Migration `f3a8c5d29014` — `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` on the 9 matchmaker-owned public tables that had RLS off (`alembic_version, attendees, conversations, grid_audit_runs, matches, messages, thread_posts, threads, users`). No policies added — the `anon` role has nothing to do here.

### Why
Supabase advisor flagged `rls_disabled_in_public` (email "Critical Issue: Table publicly accessible"). With RLS off + tables granted to `anon`, anyone with the project URL + anon key could read/edit/delete. Frontend doesn't use the anon key (verified — no `@supabase/supabase-js` imports), backend uses `postgres` role via `DATABASE_URL` which bypasses RLS as table owner. Locking anon out is safe.

### NOT touched (deliberately)
`cold_outreach`, `nominations`, `speakers` — RLS already on with intentional anon policies (1000 Minds shared tables in the same Supabase project, not ours).

### Verified
- `alembic upgrade head` applied cleanly.
- All public tables now `rowsecurity = true`.
- `SELECT COUNT(*) FROM attendees` as postgres role: 130 rows — owner bypasses RLS, backend unaffected.

### Important follow-ups
- **Rotate the Supabase DB password** — it leaked into Claude's terminal output during diagnosis (stripped only the literal "PASSWORD" keyword from the .env line, not the value). Fresh password via Supabase Dashboard → Database → Reset Password, then update `.env` + Railway env vars.
- The Supabase advisor warning email may take up to ~1h to re-evaluate and clear.

## 2026-04-30 — Three daily-sync gaps closed: match refresh, ticket_bought_at, grid audit 401

### What
Daily sync audit revealed three issues at 02:00–02:30 UTC; all three fixed and verified.

1. **Daily match refresh job didn't exist.** Despite docs claiming a 02:00 cron, the scheduler in `app/main.py` only had Extasy/speakers/grid-audit. New attendees from each day's sync got embeddings but no matches. Last matches were generated 2026-04-28; the 5 Rhuna arrivals from this morning had zero.
   - Added `refresh_matches_for_new_attendees()` in `app/services/matching.py`: finds attendees with embeddings but no entries in `matches`, runs the 3-stage pipeline for each. Preserves accept/decline state on existing matches (unlike `generate_all_matches()` which wipes the table).
   - Added `_daily_match_refresh()` scheduler hook at 02:45 UTC (after grid audit at 02:30).
   - Smoke test: 12 attendees processed, 49 matches created. The 5 Rhuna arrivals from today now have 5–8 matches each at avg score 0.71–0.74.

2. **`ticket_bought_at` never populated by the scheduled sync.** `app/services/extasy_sync.py` (the service the scheduler calls) wasn't writing the column, even though the standalone `scripts/ingest_extasy.py` does. Worse, the column wasn't declared on the SQLAlchemy ORM, so even after I added the assignment, SQLAlchemy ignored it on UPDATE.
   - Declared `ticket_bought_at: Mapped[datetime | None]` with `DateTime(timezone=True)` on the `Attendee` ORM (alongside `extasy_order_id` and `country_iso3`).
   - Added `_parse_extasy_dt()` helper in `extasy_sync.py` (parses Extasy's space-separated format to UTC-aware datetime).
   - Set `ticket_bought_at` on the new-row INSERT branch and the existing-row backfill branch.
   - Smoke test: 47 backfilled in one run; coverage went 81/128 → 128/128. Latest timestamp now reflects today's order at 15:57 UTC.

3. **Grid audit logged 0/0/0 today — root cause: 401 on Supabase REST.** `grid_audit._fetch_attendee_domains()` was using `SUPABASE_SERVICE_ROLE_KEY` against `/rest/v1/attendees`. Yesterday's RLS migration likely involved a key rotation that wasn't reflected in Railway's env vars.
   - Refactored `_fetch_attendee_domains()` from sync `httpx.Client` + REST → async SQLAlchemy session via `async_session()`. Eliminates the service-role-key dependency entirely (one less secret to keep in sync, and we use the same DB connection pool as the rest of the app).
   - Smoke test: today's failed audit row replaced with a green run — 85 domains, 25 matched (1 new since yesterday), 105 attendees, 34 matched. Duration 76s.
   - Side-effect: the sync function is now properly async, no more event-loop blocking.

### Why now
Karl-style question — "did today's sync run?" — surfaced the gaps. The failure modes were silent (matches table was the only smoking gun, and only because we knew where to look). Without these three fixes, every daily sync would continue partially-working and partially-silent.

### Files touched
- `backend/app/main.py` — added `_daily_match_refresh()` + 02:45 UTC scheduler entry
- `backend/app/services/matching.py` — added `refresh_matches_for_new_attendees()`
- `backend/app/services/extasy_sync.py` — added `_parse_extasy_dt()`; set `ticket_bought_at` on insert + backfill
- `backend/app/models/attendee.py` — declared `ticket_bought_at` ORM column
- `backend/app/services/grid_audit.py` — refactored `_fetch_attendee_domains()` to SQLAlchemy; dropped `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` reads

### Verified
- Local smoke tests for all three (above).
- Production state after smoke: 128/128 ticket holders have `ticket_bought_at`; 5 new attendees have matches; grid_audit_runs latest row green (id `1890fdae…`).

### Not yet
- Railway deploy: pushed (next commit). Tomorrow 02:00–02:45 UTC will be the first scheduler-driven proof.
- `SUPABASE_SERVICE_ROLE_KEY` env var on Railway is now unused by app code; safe to leave or remove. CLI scripts under `backend/scripts/` still use it — refresh from Supabase dashboard if running them locally.
- Alembic migration for `ticket_bought_at` column declaration not strictly needed (column already exists in DB from `supabase_setup.sql`); ORM-only change. Same pattern as `extasy_order_id` + `country_iso3`.

## 2026-05-01 — LinkedIn enrichment redesign: rip out linkedin-api, lean on Playwright

### What
Today's daily-sync verification surfaced that LinkedIn enrichment had been silently 0% for three days (2026-04-29 → 2026-05-01: 0/20 new arrivals enriched). Live test against today's only new arrival (Daniel Schwarz) confirmed: `linkedin-api` library can still authenticate but every profile-detail fetch returns 403. Account flagged.

After discussion with Shaun: **remove the linkedin-api path entirely; make manual Playwright the primary tool; keep cookie-Voyager as best-effort fallback; surface the silent-fail mode on the dashboard.**

### Changes
- **`backend/app/services/enrichment.py`** — Removed `_get_linkedin_client()` singleton, `_enrich_linkedin_api()` (the 403'd path), and `_enrich_linkedin()` (defunct Proxycurl). Simplified `_verify_linkedin_identifier` to use only the Voyager cookie. Updated `enrich_attendee` so LinkedIn enrichment only runs when `LINKEDIN_LI_AT_COOKIE` is set; saves resolved URLs to `attendee.linkedin_url` even when the fetch fails so the dashboard can link out and the Playwright script's later pass benefits.
- **`backend/scripts/linkedin_scrape.py`** — New `_is_already_enriched()` helper (checks `enriched_profile.linkedin.headline`); default behavior now skips already-enriched attendees. New `--include-enriched` flag re-scrapes everyone with a URL when needed. Existing `--dry-run`, `--limit`, `--discover`, `--only-missing` flags unchanged.
- **`backend/app/api/routes/dashboard.py`** — Two new fields on `profile_completeness`: `with_linkedin_data` (counts attendees with a real scraped headline, not just a URL) and `pending_linkedin_enrichment` (have URL but no scraped data — the queue for the next Playwright run).
- **`frontend/src/api/client.ts` + `Dashboard.tsx`** — Type updated; "LinkedIn URL" + "LinkedIn data" now shown as separate progress bars; amber alert banner appears below the Profile Quality bars whenever `pending_linkedin_enrichment > 0`, telling the operator to run the Playwright script.
- **`backend/tests/test_enrichment.py`** — Two Proxycurl-specific tests removed (tested deleted code).

### Why
Splitting LinkedIn enrichment off the daily auto-sync means: (a) the cron is never blocked on a manual login, (b) downstream Grid + match refresh always run, (c) operator runs the Playwright script on their own cadence when at the laptop, (d) the next 02:45 UTC match refresh picks up newly-enriched attendees automatically.

### Verified
- Local smoke test of dashboard counters: 142 total / 102 with URL / 94 with data / **8 pending** — actionable.
- Playwright script `--help` shows new flag; default-skip logic doesn't break existing flags.
- Frontend `npm run build` passes (CSS warning is preexisting, unrelated).
- `python3 -c 'import ast; ast.parse(...)'` clean on all edited Python files.

### Not yet
- Run the Playwright script (`python scripts/linkedin_scrape.py`) to clear today's 8-attendee queue. Manual, operator-driven by design.
- `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` env vars on Railway are now unused by app code (kept locally for the legacy `scripts/enrich_and_embed.py`). Safe to remove from Railway whenever convenient.
- `scripts/enrich_and_embed.py` still has its own copy of `_get_linkedin_client` — out of scope for this change. Will fail silently the same way the service path did until cleaned up.

## 2026-05-01 — Playwright run + bad-URL cleanup + weekly reminder routine + Phase 2 plan

### Playwright run (operator-driven, ~18:00 local)
- Logged in manually; script processed the 8 pending attendees in ~5 min.
- Result: **1 wrong-person enrichment** (Alexandra Lloyd matched to "Immigrant Justice Corp Attorney" — not the YouHodler attendee), **7 "private/blocked"** outcomes mostly because the auto-resolved URLs were garbage.
- Reverted Alexandra's enrichment via SQL: `UPDATE attendees SET enriched_profile = enriched_profile - 'linkedin' - 'linkedin_summary' - 'linkedin_enriched_at' WHERE email = 'alexandra@youhodler.com'`.
- Nulled out 2 obviously-bogus 1-4-char vanity URLs (`/in/th` Tom Horner, `/in/to` Tommi Vuorenmaa) — these came from `enrichment.py`'s URL-resolution heuristic, which previously accepted any `status_code in (200, 403)` as "verified" and stamped onto rows during past auto-runs.
- Pending queue: 8 → 6 (the remaining 6 are longer first-last-slug guesses; could be private profiles owned by the right person, or wrong-person URLs we'll clear after a future Playwright pass returns "private/blocked" again).
- Final dashboard counters: 142 total / 100 with URL / 94 with data / 6 pending.

### Weekly reminder routine
- Created `trig_014y5YF5MyAHgVG4CQ2e2c9a` — Mondays 08:02 UTC (09:02 BST). Queries Supabase for the current pending-LinkedIn-enrichment count and posts a one-line reminder. Read-only, Bash + Read tools, Supabase MCP attached. URL: https://claude.ai/code/routines/trig_014y5YF5MyAHgVG4CQ2e2c9a

### Phase 2 strategy + research
- Shaun shifted focus: what makes attendees open the matchmaking app twice (return-visit drivers).
- Spawned a research agent on competitive matchmaking apps (Brella, Grip, Whova, Bizzabo, Cvent, Hopin, Sched, Swapcard, EventMobi) — see `whats_next.md` `## Phase 2 build order` for the full validated plan and competitor citations.
- **Confirmed**: emails re-enable next week, so Phase 2 features can assume mutual-match emails fire.
- **Headline shifts from initial draft**: profile-views counter killed (no B2B competitor surfaces it; surveillance vibes); sector pulse moved from in-app to email-only; "what changed" simplified to drop rank-movement language; **5 new features added** that the research surfaced (free-slot visibility, mutual-match in-app inbox, pre-event countdown/checklist, "who else from your sector", auto-rebook on cancel).
- Top of the build queue: **free-slot visibility on match cards** — Brella signature, single highest lift because the calendar is the killer return-driver in every competitor.

### Why no implementation today
- Context budget: at ~133% during Phase 2 planning. Started a fresh build-session on Monday to ship #1 (free-slot visibility) end-to-end rather than half-build it now.
- Living plan persisted in `whats_next.md` so any session can pick it up cold.

## 2026-05-01 (later) — Phase 2 #1: Free-slot visibility on match cards

- **Backend** — `app/services/slots.py` (new): `CONFERENCE_SLOTS` mirror of frontend constant (27 thirty-min slots across June 2 + 3), plus `busy_slots_for(attendee)`, `mutual_free_slots(a, b, limit=4)`, `has_conflict(attendee, when)` helpers. Naive UTC datetimes match the existing `meeting_time` storage format.
- **Backend** — `MatchResponse.mutual_free_slots: list[datetime]` added to `app/schemas/attendee.py`. Populated in both `GET /matches/{attendee_id}` and `GET /matches/m/{token}` only when the match is mutual and not yet booked. Avoids extra round-trips: the existing match list endpoint now ships everything the UI needs to render free-slot chips.
- **Backend** — `PATCH /matches/{match_id}/schedule` now rejects with **409 Conflict** if either party already has a meeting at the requested time (skipped on idempotent re-save of the same time). Stops two attendees double-booking the same slot via the now-faster one-click path.
- **Frontend** — `Match.mutual_free_slots?: string[]` on the Match type; `formatSlotChip(iso)` helper renders compact "Mon 09:30" labels.
- **Frontend** — `MyMatches.tsx`: above the existing "Save a preferred time for Paris" expander on every mutual-match card, a new "Both free at — tap to book" panel renders up to 4 chips. One click books. Existing expander stays for overflow ("See all times" when chips are present, original copy when not).
- **Frontend** — `useScheduleMeeting` hook now also invalidates the matches query on 409 so a stale chip disappears the moment the slot is taken by another match.
- **Smoke tests** — `python -c` import + slot-helper sanity (27 slots, busy-set filtering correct); `tsc -b && vite build` passes; backend route imports clean. Full pytest skipped (pytest not in venv). Acceptable per smoke-test policy because the change is contained behind a defaulted-empty field and a 409 branch.
- **Out of scope (deliberate)** — admin `AttendeeMatches` view: chips not surfaced because admins don't book. Briefing page: read-only, no booking flow. `MagicMatches` magic-link page: would require a separate `PATCH /matches/m/{token}/schedule` endpoint — Phase 2 #1 stays auth-only for now.

## 2026-05-04 — Master speaker sheet ingested (143 new SPEAKER/VIP attendees)

### What landed
- **`backend/scripts/ingest_speakers_sheet.py`** (new) — CLI for upserting the POT26 master Speaker Tracking Google Sheet (sheet ID `1DJJ5vQ-…`) into `attendees`. Default reads `backend/data/pot_speakers_master.csv`; `--fetch` pulls fresh from Google before ingesting; `--dry-run` previews. Maps Category="Jury*"→VIP, else→SPEAKER. Bio→`goals`, LinkedIn URL→`linkedin_url`, Twitter URL→`twitter_handle`. Dedup by email then by name+company.
- **`backend/data/pot_speakers_master.csv`** (new) — committed snapshot of the master sheet (177 lines incl. header preamble; 144 valid speaker rows).
- **`backend/app/services/speakers_sheet_sync.py`** (new) — async wrapper that imports the script's `run()` and offloads to `asyncio.to_thread`. Used by the daily cron and the admin dashboard endpoint.
- **`backend/app/main.py`** — `_daily_speakers_sync()` cron at 02:15 UTC switched from `app.services.speakers_sync` (read 1000 Minds Supabase `speakers` table — only 8 rows) to `app.services.speakers_sheet_sync.sync_speakers_sheet(fetch=True)` (pulls fresh Google Sheet).
- **`backend/app/api/routes/dashboard.py`** — `POST /dashboard/sync-speakers` swapped to the new path.

### Email cleanup heuristics
The master sheet's "Speaker / Moderator E-Mail" column has two recurring data-quality problems:
1. **Multiple emails crammed into one cell** (newline- or whitespace-separated). Fix: `pick_speaker_email()` splits on `\s,;` and picks the candidate whose local-part matches the speaker's name. Critical bug along the way: original `parse_csv` used `csv_text.splitlines()`, which strips embedded newlines inside quoted cells — switched to `io.StringIO` so e.g. `rodrigo@…\ncaroline@…` parses as two candidates instead of one concatenated junk string.
2. **EA / colleague email in the speaker column** (e.g. `lplatt@mgroupsc.com` for Steven Goldfeder). Fix: `email_belongs_to()` requires the local-part to contain the first or last name (≥3 chars) or match a `f.last`/`flast` initials pattern. Short alphabetic local-parts (≤3 chars) only pass when the first letter matches an initial — catches typos like `7@nazare.io`. Rejected cells fall back to a `{slug}@speaker.proofoftalk.io` placeholder and the original cell value is recorded under `enriched_profile.suspicious_email_in_sheet` for ops to audit.

### Run results
- **Dry-run**: 144 inserts, 0 errors. ~70 placeholder emails (48 sheet cells were empty + 22 wrong-person cells we rejected); ~74 real emails accepted.
- **Live ingest**: **143 inserts, 1 unchanged** (Xavier Gomez — already in the DB from Jessica's earlier sync), **0 errors**.
- **DB state after ingest**: 315 attendees total (was 172). Breakdown: 132 SPEAKER, 129 DELEGATE, 54 VIP. Of the 22 "suspicious_email_in_sheet" rows, the speaker is matchable by name; ops should audit and overwrite the placeholder with the real email when they have it.

### Why we replaced Jessica's sync path instead of running both
The old `speakers_sync.py` reads `speakers` table where `is_live = true` — only 8 rows, all already in `attendees`. The Google Sheet is an order-of-magnitude richer (144 speakers with bios, LinkedIn URLs, Twitter, conference categories) and is the source of truth ops actually maintains. Keeping both syncs would just mean a redundant 02:15 read of an empty table; the 8 existing speakers stay in `attendees` untouched. Per Shaun: "replace Jessica's with the new file and retain the speakers from Jessica's list" — the existing 8 rows are not deleted, the cron just stops re-reading her table.

### Verified
- `from app.services.speakers_sheet_sync import sync_speakers_sheet` imports clean.
- `from app.main import app` boots clean (cron registration unchanged in shape).
- DB row count went 172 → 315 with no errors; 0 enum-mismatch failures despite the model declaring lowercase `TicketType` values while the Postgres enum stores uppercase (the script writes uppercase strings via REST, matching what `ingest_extasy.py` already does).

### Not yet
- Run enrichment + match-gen for the 143 new attendees (kicked off in background).
- The old `app/services/speakers_sync.py` file is left in place — no caller references it after this change. Will delete in a follow-up once we're confident the new path runs cleanly through one cron cycle.
- 22 suspicious-email rows: ops to audit `enriched_profile.suspicious_email_in_sheet` against the master sheet and patch real emails by hand.

## 2026-05-13 — Big run-up day: heartbeats green, branding shipped, self-enrichment incentives + Requests tab

### Cron hardening
- **Heartbeat retry** (`459a6b0`) — `_run_with_heartbeat` now retries the `sync_status` upsert once on DBAPIError/OperationalError/InterfaceError. Two cron failures this morning (speakers + enrichment_sweep) lost their heartbeats to a Supabase pooler drop and showed as stale on the dashboard even though the jobs ran.
- **Railway env-var fix** — `SUPABASE_SERVICE_ROLE_KEY` was truncated on Railway to 116 chars (full key is 219). Caused 401 on every enrichment_sweep call. Restored the full key.
- **Manual sweep** — ran `daily_enrichment_sweep` end-to-end after the key fix: 362 ok / 0 errors. All 5 daily crons should now run green.

### Enrichment depth fix + backfill
- `linkedin_scrape.py` now clicks "…see more" expanders, anchors About-section scraping to `section[id*="about"]`, and bumps truncation 200 → 1500 chars (shipped `b3f763b`).
- **Backfilled 180 attendees** by rebuilding `linkedin_summary` from the existing full `enriched_profile.linkedin.summary` we'd been storing all along but truncating to 200 chars in the combined field. No re-scrape needed.
- Refreshed AI summary + embedding for 279 LinkedIn-enriched profiles → match-gen → **1385 matches, avg 0.734**.

### Brand assets
- Real POT logo shipped (`cd3a9d8`) — replaced the placeholder CSS-clipped orange polygon with the wordmark + square mark supplied by ops. Favicon, apple-touch-icon, Open Graph + Twitter card meta all wired.

### Register flow
- **Critical fix** (`9ea8f2b`) — register endpoint was rejecting every Extasy ticket buyer because their attendee row already existed (cron-created). Now LINKS the new user to the existing attendee and merges supplied fields. Closes the gap that blocked Shaun's colleague from registering.

### Match visibility
- **Requests tab** (`e487ca1`) — new tab on MyMatches that surfaces pending "I'd like to meet" requests with an orange banner + pulsing-dot tab badge. Closes the notification gap until email re-enable.
- **Two-pass match fetch** (`40e10a5`) — `/matches/{attendee_id}` was only returning top-N by score, so low-score pending requests (Sithum→Zohair, 0.78, rank ~12 of 46) were invisible on the recipient's frontend. Now always appends pending-request rows regardless of rank.

### Self-enrichment incentives (#1 + #2 of the 5-mechanic plan)
- **Locked-match preview** (`59ecc88`) — `MyMatches` now gates how many matches a regular user can see based on profile-completeness %. Below the gate: a dashed-orange "N more matches hidden" card with a "Unlock my matches" CTA → /profile. Admins are exempt.
- **Match-quality benchmark banner** — top of MyMatches shows the user's average match score vs the 0.85 rich-profile benchmark, with the lift number quantified. Auto-hides at ≥80% completeness.
- Util: `frontend/src/utils/profileCompleteness.ts` (8 equal-weight fields, plus `visibleMatchLimit` for the gate logic).
- Next on the plan: #5 (concierge offers to draft missing fields with GPT) — captured in `whats_next.md` for a fresh session.

### Misc
- Sliding-token refresh middleware + Extasy 5-min cache (`cb98733`) — kills mid-event logouts and dashboard hot-fetching.
- Dropped 5-attendee demo fallback in `useAttendees` (`20f0ef8`) — was causing a flash of fake data on login.
- Attendee list cap raised 200 → 1000 (`c982ce1`) — search was silently truncating past row 200.
- Manual enrichment for Sithum (just registered today) — Grid + website + LinkedIn + photo all captured; 4 matches generated.
- Exported speaker emails for Zohair: `backend/exports/pot_speakers_emails_20260513.xlsx` (83 real + 65 placeholder).

## 2026-05-13 (evening) — Phase 2 #5 shipped: AI Concierge proactively drafts missing profile fields

Closes the self-enrichment loop kicked off this morning: incentives #1 (locked-match preview) and #2 (match-quality benchmark) showed users *why* they should finish their profile; #5 now does it *for* them.

### Flow (verified end-to-end in browser against Mona Bauer, 50% complete)
1. User opens AI Concierge → `GET /chat/profile-prompt` returns the next missing high-impact field (goals → target_companies → interests, in that priority).
2. Tailored welcome replaces the generic "Hello!" — "Your profile is 50% complete — I can draft your conference goals based on your role and profile."
3. Yes → `POST /chat/draft-field` → GPT-4o returns 2–3 grounded candidates (3 for PARTIAL/GOOD profiles, 2 with a "starting points — feel free to rewrite" hint for SPARSE).
4. Click a candidate → inline textarea pre-filled → edit → Save.
5. `POST /chat/save-field` persists the value, marks `enriched_profile.field_prompts.{field} = {state: "accepted", last_offered_at: …}`, schedules a background `process_attendee` + `generate_matches_for_attendee` refresh.
6. Confirmation card: "Saved. I've kicked off a match refresh in the background — new recommendations will appear shortly."
7. Maybe later → `POST /chat/decline-prompt` → `state: "declined"`, suppressed for 30 days, offer rotates to the next priority field on next visit.

### Files
- **New:** `backend/app/api/routes/chat.py` got 4 endpoints (`/profile-prompt`, `/draft-field`, `/save-field`, `/decline-prompt`). `frontend/src/components/chat/ProfilePromptOffer.tsx` for the four-phase offer UI (idle → picking → editing → saved).
- **Edited:** `backend/app/services/concierge.py` — `select_next_field_to_offer`, `draft_field_candidates`, `profile_data_quality` (now the single source of truth for SPARSE/PARTIAL/GOOD — also called by `_brief_attendee_line` so the anti-hallucination posture stays in sync), `mark_field_prompt`, `compute_completeness_pct`. `backend/app/schemas/chat.py` — 5 new Pydantic models. `frontend/src/api/client.ts` — 4 new fetch helpers + `OfferableField` type. `frontend/src/hooks/useChat.ts` — fetches the prompt on mount, exposes `profilePromptOffer` + `dismissProfilePromptOffer`. `frontend/src/components/chat/ChatPanel.tsx` — renders `ProfilePromptOffer` when an offer exists, falls back to generic welcome otherwise.

### Smoke tests
- 8 unit smokes on `select_next_field_to_offer` covering all-empty / priority rotation / 80%-threshold / 30-day decline cooldown / SPARSE bucket — all green.
- Live HTTP curl: auth, empty-value rejection, full draft → save loop, completeness rotation 50% → 67%.
- Live browser flow against `localhost:5277` + `localhost:8000` → Mona Bauer's offer rendered, GPT drafted 3 specific candidates ("Establish 3 partnerships with AI/Web3 ecosystem foundations…"), save succeeded, DB row mutated correctly, background re-embed completed without errors, reload rotated the offer to `target_companies` (the next priority field), Maybe-later persisted `declined` with timestamp.
- Test mutation reverted: Mona's row restored to empty `goals` + cleared `field_prompts`.

### Design + spec
- Brainstorm + design doc: `docs/superpowers/specs/2026-05-13-concierge-field-drafting-design.md`. Resolved during brainstorming: offer surface (starter message + chips), fields in scope (goals + target_companies + interests, not photo), save UX (chip → editable textarea → Save), persistence (per-field state map with 30-day decline cooldown), completeness denominator (6 fields).

### Anti-hallucination posture
- `profile_data_quality()` is now a single helper used by both the concierge context builder and the new drafter. SPARSE profiles get 2 generic "starting points" candidates instead of 3 specific ones, and the system prompt explicitly forbids inventing fund sizes, products, theses not grounded in the input.

## 2026-05-13 21:35 — Photo-upload nudge in AI Concierge (follow-on to field-drafting)

Extended the `ProfilePromptOffer` flow to nudge for `photo_url` once the GPT-drafted fields are filled. Photo is in the completeness denominator but was previously unreachable: an 83% attendee with only photo missing got `field=null` because the GPT offer set excluded it. Now the offer rotates: goals → target_companies → interests → photo_url, and photo bypasses the < 80% completeness gate (no GPT call to gate against).

### Backend
- `app/services/concierge.py` — `OFFERABLE_FIELDS` extended with `"photo_url"`. New `GATE_BYPASS_FIELDS = {"photo_url"}` and `select_next_field_to_offer` rewritten to apply the 80% gate only to GPT-drafted fields. Photo nudge fires at any completeness level if photo is missing and not recently declined.
- `app/api/routes/chat.py` — `save-field` accepts `photo_url`, validates `http(s)://` prefix, writes `attendees.photo_url`, skips the background re-embed (photo doesn't affect matching, saves an OpenAI call + match-gen round-trip).
- `app/schemas/chat.py` — `OfferableField` literal includes `"photo_url"`.

### Frontend
- `components/chat/ProfilePromptOffer.tsx` split into two branches: `DraftOffer` (existing GPT flow) and new `PhotoOffer` (URL paste + Save / Skip, no candidates step). Photo branch uses the same idle/saving/saved phase pattern. Camera icon instead of Sparkles in the avatar slot.
- `api/client.ts` — `OfferableField` type extended.

### Smoke tests
- Round-trip against a real attendee (Lamar Ellis) set to "only photo missing" state: `select_next_field_to_offer` returned `photo_url` at 83% complete ✓; save with a https URL took the attendee to 100% with `field_prompts.photo_url.state="accepted"` ✓; decline path persisted `declined` with timestamp and suppressed the offer ✓; attendee row reverted to original state.
- Vite production build: 2047 modules, 1 unrelated CSS warning, 0 TS errors.
- No real attendee currently sits at "only photo missing" in production (most users still missing goals/targets/interests too); offer will surface organically as users complete the GPT-drafted fields.

### Out-of-scope
- File-upload affordance: the platform has no object-storage backend (auth/profile + magic-link both take photo URLs). Adding file-upload would need new infra. URL paste matches the existing system and shipped in scope.

## 2026-05-15 09:55 — LinkedIn photo backfill resumed (LinkedIn unblocked)

- LinkedIn accounts unblocked after the 2026-05-12 rate-limit pause. Ran `scripts/linkedin_scrape.py --missing-photos-only --limit 30` against the 143-row queue.
- Result: 25/30 enriched, 5 skipped (private/blocked profiles), 0 errors. Photo count: 156 → 174 (+18). Pending queue: 143 → 125.
- Tweaked scraper queue ordering to `created_at.desc` so the latest registrations (who need matches now) get photographed first when batches are rate-limit-capped. Older missing-photo rows can wait one more day.
- Spotted a duplicate Stani Kulechov row in `attendees` — real `stani@aave.com` (Rhuna registration today) vs `stani.kulechov@speaker.proofoftalk.io` placeholder from the May 4 speaker-sheet sync. Logged for dedup follow-up in `whats_next.md`. Speaker-sheet sync doesn't currently merge on `linkedin_url`.
- ~7 enriched profiles didn't yield a photo URL despite the scraper marking them ✅. Likely LinkedIn's lazy-loaded avatar element not present at scrape time — separate fix.

## 2026-05-15 10:30 — Post-batch cleanup: dedup, name backfill, richer AI summaries

Three issues surfaced when Shaun spot-checked the photo batch in the app; all addressed before the next scrape.

### 1. Stani Kulechov dedup
- Speaker-sheet sync (May 4) had created a placeholder row (`stani.kulechov@speaker.proofoftalk.io`, "Aave Labs") with 8 matches. Today's Rhuna registration created a second row (`stani@aave.com`, "Aave") with 0 matches.
- Resolution: deleted the new orphan row, then updated the placeholder row's email → `stani@aave.com` and company → `Aave`. All 8 matches preserved on the canonical row.
- Order matters: `attendees_email_key` unique constraint forces delete-orphan-first before update.

### 2. First-name-only name backfill (Gavin Zaentz)
- Audit found 2 single-word-name attendees with linkedin_url: Gavin (Zaentz) and Shaun (Kanyuchi). Gavin was hard to find via in-app search because his stored name was just "Gavin".
- Manual fix: `update attendees set name = 'Gavin Zaentz', title = 'Co-Founder' where id = '539a656a-…'`. Shaun's own row left as-is.
- Long-term fix added to `scripts/linkedin_scrape.py`: when the DB name is single-word, the scraper now backfills the surname from the scraped page-title name, falling back to title-casing the LinkedIn URL slug (`gavin-zaentz` → "Gavin Zaentz"). First-name match required as a safety check so we don't overwrite with a wrong-person name.

### 3. AI summary now surfaces LinkedIn About content
- Old `generate_ai_summary` dumped the full enriched_profile dict into the prompt but the rules were defensive ("DO NOT invent…") with no instruction to *use* the LinkedIn About. Result: Chiara Munaretto's summary leaned on Grid data only ("Managing Partner at Stablecoin Insider… Specific interests or goals have not been disclosed") and never mentioned her PoT marketing role, Web3 Deloitte advisory, or 20+ Web3 events organised — all explicit in her LinkedIn About.
- Rewrote the prompt in both `app/services/embeddings.py` (ORM-attendee version) and `scripts/enrich_and_embed.py` (dict version, used by the refresh script). New prompt extracts `linkedin.headline` + `linkedin.summary` + Grid + website summary into named fields, instructs to lead with role + company, then "surface the most match-relevant signals from their LinkedIn About — domain expertise, past roles or exits, products/funds/protocols they've built". Guardrails kept (no invented theses; "actively seeking" only if Goals say so; LinkedIn About is biographical history not current intent).
- Bumped max_tokens 200 → 400 to fit the richer summary.
- Smoke-test on Chiara + Joris: both summaries now include real LinkedIn-grounded specifics (Joris's Nexteem exit, two decades of company-building, work with top European banks; Chiara's PoT marketing lead role, 20+ Web3 event organising, Web3 Deloitte advisory on Crypto Custody). The "Specific interests or goals have not been disclosed" close is preserved where both fields are empty — no fabrication.
- Bulk regen kicked off via `scripts/refresh_summary_after_linkedin.py` (CUTOFF set to 2024-01-01 to refresh ALL 174 LinkedIn-enriched attendees). Each run regenerates ai_summary + intent_tags + deal_readiness_score + embedding so the matching engine reflects the richer summary too. Cost ~$0.55 total.

### 4. Sentence-aware truncation for `linkedin_summary`
- `enriched_profile.linkedin_summary` (the convenience field rendered in the admin "Enriched Data" panel) capped at exactly 1500 chars, producing mid-word cuts ("…what I call being a horizonta", "…mentoring coll"). Bumped cap 1500 → 2500 and now cut at the last `. / ! / ?` before the cap, appending " …" so the truncation is visible. Falls back to a hard cut only if no sentence boundary exists in the back half of the string.

## 2026-05-16 12:25 — Launch video script: language + structural pass to match the app

- Reviewed [launch/POT Matchmaker — Video Script.docx](launch/POT%20Matchmaker%20—%20Video%20Script.docx) (76.3s, 20 scenes, 4 acts) against the actual app UI strings and rewrote on-screen text to mirror the product. Created a markdown companion `launch/POT Matchmaker — Video Script.md` and regenerated the `.docx` from it, following the same `.md ↔ .docx` pairing already used for `sithum-script-2026-05.*`. Structure, scene count, timestamps, music/SFX direction, animations, and export deliverables all preserved — only on-screen text and two scene rebuilds changed.
- **Scene 07 (My Matches)** — replaced "DEAL READY: %" (which conflated the match-type label with a score) with "COMPATIBILITY: %", and varied the three cards across all three real match types from `frontend/src/utils/matchHelpers.tsx:82-105`: Complementary / Non-Obvious / Deal Ready. Reason label changed from "Why this matters" to the app's actual "Why this meeting matters".
- **Scene 09 (Concierge Chat)** — added the real input placeholder "Ask about attendees, meetings, connections…" from `ChatPanel.tsx:180`.
- **Scenes 10/11** — renamed chapter card "Auto Profile" → "Drafted for you" and rebuilt Scene 11 around the actual `ProfilePromptOffer.tsx` flow: Concierge welcome bubble → "Yes, draft my goals" + "Maybe later" pills → three candidate chips → tap → "Saved. Matches refreshing." (Replaces the form-fill UX which doesn't exist in the product.)
- **Scene 13 (Mutual Match)** — banner now reads the app's actual copy "Mutual match — both accepted!" (from `MyMatches.tsx:649-651`).
- **Scene 15 (One-tap Booking)** — header swapped to the real chip text "Both free at — tap to book". The "Calendar invite sent to both of you" line dropped — that feature isn't built today; replaced with "Locked in. They'll see it in their matches too."
- **Scene 17 (Magic Link)** — revised per Z's "less words, more punch" preference: single seamless email→landing transition (email subject `"Your introductions are ready, Mira."` + CTA → cursor tap → magic-link landing "Welcome, Mira" + 3 mini match cards). Drops the 3-row meeting list. Uses real strings from `email.py:167` and `MagicMatches.tsx:94`.
- **Scene 18 (Impact close)** — replaced with the home-page hero line from `frontend/src/pages/Home.tsx:19-24`: "Tell us what you need. / We'll tell you who to meet." (Two lines instead of three, more room for the brief's "trust the gaps" tone direction.)
- **Scene 19** — typo fix "Build Into" → "Built Into".
- Round-tripped through pandoc 3.9: smoke-grep confirms all revised strings present in the .docx (Why this meeting matters: 4 hits, COMPATIBILITY: 82%: 1, Mutual match — both accepted: 1, Welcome, Mira: 1, etc.) and all removed strings absent (DEAL READY: 82%, Calendar invite sent, MY CONFERENCE GOAL, 3 MEETINGS LOCKED IN, Auto Profile: 0 hits each).

## 2026-05-16 13:20 — Applied script edits to Sithum's React renderer

- Sithum shared the video source: a React 18 + Babel-in-browser renderer (`animations.jsx` + `video.jsx` for scenes 01–06 + `video2.jsx` for scenes 07–20 + `app.jsx` orchestrator with a 20-scene SCHEDULE at 76.3s/60fps). Files dropped into [launch/from_sithum/](launch/from_sithum/) (untracked — gitignored as ~22MB of binary assets).
- Per Shaun's "we do a copy for ourselves then compare" direction: cloned to [launch/our_version/](launch/our_version/) and applied all on-screen text edits there, leaving `from_sithum/` pristine for a clean diff later. Only `.jsx`/`.html`/README committed; the 22MB of MP3/PNG assets stay in `from_sithum/` and are copied at runtime per the README.
- All edits landed in `video2.jsx`. Note: Sithum's component numbering is offset from the script's scene numbers (his `Scene07` = our Scene 7, but his `Scene09` = our Scene 11, etc.) — translation table in `launch/our_version/README.md`.
- **Scene 07 (My Matches)** — refactored `MatchCard` to accept `matchType` + `matchTypeDescriptor` props; each of the 3 cards now spans a different real match type (Complementary / Non-Obvious / Deal Ready) per `matchHelpers.tsx:82-105`. Right-column score label "DEAL READY" → "COMPATIBILITY". Reason prefix "Why this matters" → "Why this meeting matters" (real app copy from `MyMatches.tsx:499`). Subtitle → "Your top introductions, ranked. Ready before you land."
- **Scene 08 (Concierge Chat)** — added a static input placeholder mirroring the real app's `ChatPanel.tsx:180`: "Ask about attendees, meetings, connections…" pinned below the chat bubbles.
- **SceneIntro09 → "Drafted for you"** — renamed from "Auto Profile" with new subtitle "Concierge drafts. You approve. Matches refresh."
- **Scene 09 (Profile)** — full rebuild around the actual `ProfilePromptOffer` chat UX: Concierge bubble (0.7s) → orange "[ Yes, draft my goals ]" + grey "[ Maybe later ]" pills (1.6s) → cursor tap (2.1s) → 3 candidate chips with 0.15s stagger (2.5s) → cursor taps chip 2 with orange border highlight (3.5s) → green "✓ Saved. Matches refreshing." banner (3.9s). Replaces the form-fill `ProfileField` rows.
- **Scene 10 (Mutual Match)** — banner copy now exactly matches `MyMatches.tsx:649-651`: "Mutual match — both accepted!"
- **Scene 11 (One-tap Booking)** — header swapped to the real mutual-free-slot chip text "Both free at — tap to book" (from `MyMatches.tsx:690-691`). Dropped the "Calendar invite sent to both of you" line — feature isn't built — replaced with "Locked in. They'll see it in their matches too."
- **Scene 12 (Magic Link)** — full rebuild around an email→landing transition. Minimal email card (POT logo + sender + subject "Your introductions are ready, Mira." from `email.py:167` + single CTA) at 0.0s → CTA scale-pop at 0.5s → cursor tap at 1.0s → card slides up and out (easeInCubic) → magic-link landing drops in at 1.4s with real heading "Welcome, Mira" (from `MagicMatches.tsx:94`) + 3 mini stacked match cards (one per match type) staggering in at 1.7s. Dropped the 3-row meeting list.
- **Scene 13 (Impact close)** — replaced 3-line serif close with the home-page hero line from `Home.tsx:19-24`: "Tell us what you need." (white, 88px Fraunces) + "We'll tell you who to meet." (orange italic, 88px Fraunces). Re-tuned timing: line 1 at 0.2s, line 2 at 1.2s.
- **Scene 14Availability** — typo fix "Build Into" → "Built Into".
- **Smoke tests:** all 4 jsx files Babel-parse cleanly (no syntax errors). String-grep confirms 19 changed strings present, 15 removed strings absent. Visual verification via Playwright at `?render=1` (which disables autoplay and exposes `window.__seek(t)`) — snapshotted Scenes 07, 09, 10, 11, 13, 14 and the rebuilt Scene 12 at their key timestamps; all render as intended. Screenshots in [.playwright-mcp/](.playwright-mcp/).

## 2026-05-16 15:10 — Concierge typewriter slowdown + Scene 09 beat reflow

- Transcribed [launch/from_sithum/voiceover.mp3](launch/from_sithum/voiceover.mp3) via OpenAI Whisper-1 with segment timestamps. Confirmed the VO is high-level/thematic — it names features ("AI concierge", "autoprofile", "mutual match") but does NOT read the on-screen Concierge chat content. So viewers DO need to read those bubbles.
- **ChatBubble typewriter speed is now tunable.** Added `typeSpeed` prop (seconds) with smart default: 1.8s for user bubbles, 2.8s for accent (Concierge) bubbles. Per-call override stays possible.
- **Scene 08 reflow** — user bubble 1 now uses `typeSpeed=1.0` (was 1.8s) and starts at 0.4s (was 0.9s); Concierge bubble starts at 1.5s (was 2.2s) so its 2.8s typewriter completes ~4.4s with ~0.7s hold; second user bubble `typeSpeed=0.8` at 4.3s (was 3.6s); typing pill moved to 4.6s. Net effect: the Concierge orange bubble reads cleanly without overlapping mid-typing.
- **Scene 09 (rebuilt) beat reflow** — Concierge bubble start pulled forward 0.7s→0.2s so the 2.8s typewriter finishes at 3.15s. All subsequent beats pushed back: buttons 1.6s→3.4s, cursor tap 2.1s→3.7s, chips 2.5s→3.9s (stagger 0.15s→0.1s to fit), chip-tap 3.5s→4.4s, banner 3.9s→4.6s. Scene still fits the original 4.90s window; banner has 0.3s visible.

## 2026-05-16 15:50 — Audio fix: mount BackgroundMusic + SyncedAudio (Sithum bug)

- User reported no sound. Diagnosed: `BackgroundMusic` and `SyncedAudio` were defined in [launch/our_version/app.jsx](launch/our_version/app.jsx) at lines 81 and 118 but never mounted in the `VideoApp()` render tree — so the `<audio>` elements never reached the DOM. Bug pre-existed in Sithum's snapshot ([launch/from_sithum/app.jsx](launch/from_sithum/app.jsx) — same issue).
- Fix: added `<BackgroundMusic />` and `<SyncedAudio />` inside the `<Stage>` alongside `<WatermarkLogo />` (lines 183-184). Stage just renders `{children}` inside its TimelineContext provider per `animations.jsx:489`, so passing audio components as children gives them access to `useTimeline()` without any other changes.
- Verified via Playwright: 2 audio elements now in DOM, both `readyState: 4` (fully loaded). music.mp3 ramps from volume=0 (2.5s fade-in per `BackgroundMusic`); voiceover.mp3 at volume=1. User confirmed audio plays after hard-reload (Cmd+Shift+R) to bust the babel-in-browser script cache.

## 2026-05-16 16:45 — VO regenerated to match the actual 76.3s SCHEDULE

- After the audio fix, user noticed the VO was out of sync with the visuals. Diagnosed against the Whisper transcript: first half (0:00-0:34) aligned, but second half drifted 6-8s ahead — "magic link" called at 0:50 while the chapter card doesn't appear until 0:56; "Built into Proof of Talk" called at 0:59 while Scene14 doesn't start until 1:07. The original voiceover.mp3 was clearly recorded against a shorter cut.
- **Regenerated VO via ElevenLabs Lauren PVC voice** (voice_id `DODLEQrClDo8wCz460ld` — found by listing voices with the new `ELEVENLABS_API_KEY` in `backend/.env`). Used `eleven_multilingual_v2` model with the original voice settings (stability 0.50, similarity 0.75, speaker boost on, speed 1.0).
- **Strategy:** 20 individual phrases generated separately, then ffmpeg-stitched with explicit silence padding via `adelay` filter so each phrase starts at a precise target time aligned to the 76.3s SCHEDULE. Each chapter card callout ("AI matchmaking", "AI Concierge", "Drafted for you", "Mutual match", "Smart booking", "Magic link") now lands within ±0.5s of its corresponding `SceneIntroXX` start in `app.jsx`.
- Final clip 21 ("Claim your ticket.") dropped — the on-screen orange CTA button + music carry the close, and the clip didn't fit before video end (76.30s) without overrunning. Two clips (5 + 6) shifted 0.7-0.9s later than originally drafted because clip 4 ("...conversation that changes your year") is naturally 5.34s long and crowded its successors.
- Final stitched runtime: **75.68s** (within the 76.30s video duration). 1.82MB MP3. Saved at [launch/our_version/voiceover.mp3](launch/our_version/voiceover.mp3) (replaces the old desynced version; only file in `our_version/*.mp3` that's now committed to git via `.gitignore` exception).
- Per-phrase script + target times: [launch/our_version/voiceover_script_v2.md](launch/our_version/voiceover_script_v2.md). Per-phrase source clips left in `/tmp/vo_segments/` (not persisted).

## 2026-05-16 17:25 — Final polish: Brian VO + audio robustness + mobile hint + MP4 export script

- User feedback after listening: VO felt disconnected ("like someone just talking while the video is playing"), wanted a male voice, music muffled Brian after 1:12, audio sometimes played music-only without Brian.
- **Voice swap to Brian** (premade voice `nPczCjzI2devNBz1zQrb` — "Deep, Resonant, Comforting"). Regenerated all 20 phrases via ElevenLabs `eleven_multilingual_v2`. Brian is faster than Lauren — final stitched runtime dropped from 75.68s to 74.10s.
- **Chapter-card callouts shifted +1s** so the VO names each feature when the title is fully sharp (the SceneIntro title has a 1.4s blur-dissolve animation). Clips 7 and 9 bumped slightly to absorb cascade overruns from clips 6 and 8. Updated [voiceover_script_v2.md](launch/our_version/voiceover_script_v2.md).
- **Fixed VO_END bug in BackgroundMusic** ([app.jsx:89](launch/our_version/app.jsx#L89)) — was hardcoded to 67.24s from the old Lauren VO's natural end. Bumped to 74.5s so music stays ducked (-12dB) for the duration of Brian's VO and only returns to full volume for the final 2s music-only tail.
- **Audio retry robustness** ([app.jsx:142-167](launch/our_version/app.jsx#L142-L167)): the original `handleTap` only retried the voiceover, so if Chrome blocked autoplay and only music started, clicking the orange "Tap to enable sound" pill wouldn't bring Brian back. New `handleTap` iterates every `<audio>` on the page and replays each. Also added a `window.click` + `keydown` capture-phase listener that fires once on any user interaction, so even users who don't see the pill get audio on their next interaction.
- **Mobile portrait rotate hint** ([index.html](launch/our_version/index.html)): added a fullscreen splash (`@media (max-width: 720px) and (orientation: portrait)`) with an animated rotate icon. The 16:9 video doesn't work well at small portrait sizes; landscape gives the full experience.
- **MP4 export script** ([render.mjs](launch/our_version/render.mjs)): Playwright drives `?render=1` mode (autoplay off + `window.__seek(t)` exposed), screenshots every frame at 60fps (configurable via `--fps=30`), then ffmpeg muxes the PNG sequence with `voiceover.mp3` + `music.mp3` (matching the same -12dB duck levels the live page uses) into an H.264 MP4 with `+faststart`. Supports 1080p default and true 4K via `--4k`. Output files gitignored (`pot_matchmaker_*.mp4`).
- README updated with audio architecture, mobile behaviour, and download instructions.

## 2026-05-16 21:40 — Preserve Rhuna granular pass names; "Ticket Types" dashboard card

- **Problem discovered today**: `extasy_sync.py` collapses Rhuna's 7 granular pass names (General / Startup / Press / Investor / VIP / VIP Black / Speaker / Sponsor) into the 4-value `TicketType` enum (DELEGATE / SPEAKER / VIP / SPONSOR). The raw name was being stashed at top-level `enriched_profile.ticket_name` for 362 attendees but nothing read it, so we lost a signal the matching engine could use.
- **Fix — schema**: granular Rhuna fields now live under `enriched_profile.extasy.{order_id, ticket_code, ticket_name, phone, city, country, paid_amount, voucher_code, synced_at}` (nested JSONB, no migration). Merge semantics in `extasy_sync.py` changed so the `.extasy` sub-key is Rhuna-authoritative (latest sync wins) while the rest of `enriched_profile` keeps existing-wins so enrichment data is never clobbered.
- **Writers updated**: `app/services/extasy_sync.py`, `app/api/routes/integration.py` (Runa webhook), `backend/scripts/ingest_extasy.py`.
- **One-shot backfill**: `backend/scripts/backfill_rhuna_pass_names.py` migrates the top-level keys into the nested namespace and strips them from the top level so we don't keep two sources of truth. Idempotent (uses `flag_modified`); falls back to the standalone `extasy_ticket_name` column if the JSONB is missing. Live run rewrote **362/362** Rhuna attendees: 244 General Pass, 46 VIP, 30 Press, 16 VIP Black, 14 Investor, 10 Startup (Application Based), 1 Media — distribution matches Rhuna's report exactly.
- **Dashboard**: `/dashboard/revenue` now includes `ticket_types_breakdown: {total, by_pass: [{pass_name, count}]}` sourced from `enriched_profile.extasy.ticket_name` (matchmaker DB = ground truth, not the live Extasy API which the revenue card already uses). New "Ticket Types (Rhuna)" card on Dashboard renders the breakdown as horizontal bars with count + %, matching the existing Registration Funnel pattern. Card is conditional on `ticket_types_breakdown.total > 0` so it disappears cleanly if data ever resets.
- **Smoke tests**: backend imports clean; `pytest`-style direct call to `revenue_stats()` returns the expected 7-row breakdown; `tsc -b` clean; `vite build` clean. UI not browser-tested (admin login required); card structure mirrors the Funnel card directly above it in the same file.

## 2026-05-17 10:55 — Sync-health panel + Matchmaking-Readiness-by-Pass cross-tab

- **Sync Health panel** (Phase #2 from yesterday's roadmap convo) — `/dashboard/revenue` now returns `sync_health[]` from the `sync_status` heartbeat table. New top-of-page panel renders one chip per cron with status badge (green OK / amber PARTIAL / red ERROR) and a colour-coded age (green <6h, amber 6–30h, red >30h). Directly surfaces the silent-failure drift mode that bit us 2026-04-28 and lay invisible for ~6 days until Karl asked about ticket counts. First view immediately surfaced a real issue: `daily_speakers_sync` returning 401 from Google Sheets (separate fix).
- **Matchmaking Readiness by Pass** (Phase #3) — same endpoint returns `ticket_types_breakdown.completeness[]`: for each granular Rhuna pass, the count + % filled on goals, linkedin_data, target_companies, photo, grid. Rendered as a colour-coded table (green ≥75% / amber ≥40% / red <40%). Immediately exposes the highest-value backfill targets: VIP Black (6% goals, 19% LinkedIn — 16 attendees) and Investor Pass (0% goals, 21% LinkedIn — 14 attendees) are the matchmaker's worst coverage among paying tiers.
- **Files**: `backend/app/api/routes/dashboard.py` (one-pass enrichment in the existing attendees loop + sync_status query), `frontend/src/api/client.ts` (type extension), `frontend/src/pages/Dashboard.tsx` (two new card components in the Revenue & Registration section).
- **Smoke tests**: backend imports clean; direct call returns 7 sync rows + 7 completeness rows; `tsc -b` clean; `vite build` clean; full browser walkthrough as admin@pot.demo passed — both new sections render with colour coding intact. Screenshot at [dashboard-sync-health-and-readiness.png](dashboard-sync-health-and-readiness.png).
- **Skipped**: the existing dashboard shows two redundant sync_status entries (`daily_extasy_sync` and `extasy_sync`) — both write the same data. Not in scope today; could be deduped by removing one of the writers later.

## 2026-05-18 12:00 — CEO Dash vs Matchmaker ticket-count gap investigation; Z landing-page draft preview

- **Question raised by Karl** — same Rhuna feed but CEO Dashboard shows 303 confirmed tickets while the Matchmaker dashboard shows 443. Revenue identical (€127.9k) on both. Root-caused by reading both code paths side-by-side: [backend/app/services/extasy_sync.py:31](backend/app/services/extasy_sync.py#L31) `VALID_STATUSES = {"PAID", "REDEEMED"}` and dedupes by email; [CEO-Dash/supabase/functions/refresh-data/index.ts:1107-1150](../CEO-Dash/supabase/functions/refresh-data/index.ts#L1107-L1150) only counts `PAID` rows with `paymentsAmount > 0` (REDEEMED has no branch, complimentary PAID-with-€0 go to a separate `compCount`). So the gap = REDEEMED + complimentary. Revenue agrees because revenue only books when `payAmt > 0` on both sides. Neither number is wrong — different audiences (finance vs ops). Drafted a WhatsApp explainer for Karl.
- **Z's landing-page draft review** — Z dropped `launch/from_Z/matchmaker.html` (280 lines, self-contained). Long-scroll marketing page: Hero (headline "Four people here will change your year") → Wound (4 blurred "ghost cards" that resolve) → Stakes (animated stats: 2,500 / $18T / 93%) → Features (6 cards) → Dream (cream-section pivot) → Close CTA. Fraunces + Poppins + Inter + JetBrains Mono type system. Loaded via Playwright at 1440px and 390px; screenshots committed at [z-matchmaker-desktop-full.png](z-matchmaker-desktop-full.png), [z-matchmaker-desktop-resolved.png](z-matchmaker-desktop-resolved.png), [z-matchmaker-mobile.png](z-matchmaker-mobile.png).
- **Critique** — Voice/aesthetic dead-on for Louvre positioning; headline is a money line. Gaps: no real product UI shown (ghost cards are pure metaphor), stats unsourced ($18T/93%), no sponsor/speaker proof, CTAs `href="#"`, no pricing surface. The headline-vs-current-`Home.tsx` swap matters: current is functional ("Tell us what you need"), Z's is emotional/sales ("Miss them and you'll never even know").
- **Preview implementation** — building Z's draft as-is into a React component at `/preview-landing`. New `frontend/src/pages/HomeLanding.tsx` ports the HTML; Layout.tsx short-circuits for this path (no nav, no chat widget — full-bleed); Google Fonts added to `frontend/index.html`. Current `Home.tsx` at `/` stays untouched so both can be compared. CTAs intentionally unwired — visual review first, decide on production rebuild scope after.

## 2026-05-18 14:05 — Manual registration + enrichment: Benedikt Hiepler (Krankikom)

- **New registration** — `benedikt.hiepler@krankikom.de` arrived outside the Rhuna feed. Created the Supabase row directly via REST (`id=ac39a857-ec96-44be-90c6-730fd70e0b03`, ticket_type=DELEGATE, company=Krankikom, company_website=krankikom.de inferred from email domain, linkedin_url from registration).
- **LinkedIn enrichment** — `python scripts/linkedin_scrape.py --names "Benedikt Hiepler"`. Playwright MCP browser was locked by a parallel Claude session, so used the operator script (the documented primary tool per CLAUDE.md). Captured headline (`Entwicklungsleiter KI-Unit bei Krankikom GmbH | Senior Software Developer | KI-Lösungen & intelligente Produkte`) and 622-char German `About` summary. `experiences` came back empty (LinkedIn's role layout didn't match the script's heuristic) and `profile_pic_url` was None — Benedikt's photo `<img alt>` doesn't contain his first name, which trips the strict name-match safety check (a known limitation on non-English profiles; not worth a script change for one row).
- **Top-level title backfilled manually** to `Entwicklungsleiter KI-Unit / Senior Software Developer` because the auto-title path only fires when `experiences[0]` is present.
- **AI summary + embedding + intent tags** — ran `refresh_summary_after_linkedin.refresh` for just Benedikt (one-row import instead of the full 312-profile sweep). Tags: `technology_evaluation`, `knowledge_exchange`; `deal_readiness_score=0` (no fundraising/dealmaking signal in his profile).
- **Match generation** — `refresh_matches_for_new_attendees(top_k=10)` picked him up automatically and produced **5 matches**: Yannik Heinze (Softstack CEO, Web3 dev/cybersecurity, 0.78 complementary), Aditya Raghavan (Google Cloud blockchain analytics, 0.74), Sebastian Felipe (Insigniatech decentralized ML, 0.72), Konstantin Richter (Blockdaemon institutional infra, 0.70 complementary), Manuel Müller (Digital Euro Association, 0.68 non-obvious). All explanations mention his AI-unit lead role at Krankikom — the LinkedIn About blob made it into the embedding correctly.
- **Smoke**: scraper exited "1 enriched, 0 errors"; match script returned `{attendees_processed: 2, matches_created: 5, failed: 0}` (Benedikt + one other newcomer in the queue); Supabase row verified by direct REST GET. Photo gap noted for the next missing-photos backfill batch — magic-link emails will fall back to Gravatar/initials in the meantime.

## 2026-05-18 14:25 — Dashboard demo-flash + /dashboard auth-guard + signout cache clear; ticket-gap precise diagnostic

Three production fixes shipped and verified live, plus a follow-up on the CEO-dash ticket-count investigation.

- **Drafted Zohaib WhatsApp reply** on how matches behave when new attendees join: nightly 03:30 UTC `refresh_matches_for_new_attendees` only generates matches for *new* rows (existing accept/decline state preserved); existing attendees only get re-ranked against newcomers in periodic full re-rank passes (planned T-2 weeks / T-3 days); ranking via 3-stage pipeline; email notifications still globally disabled in code (`send_match_intro_email` returns early with "BLOCKED").

- **Ticket-count gap precise diagnostic** — wrote `backend/scripts/diagnose_ticket_count_gap.py`. Hits live Rhuna, applies both CEO-dash and matchmaker filters in parallel, lists every row each side counts differently, reconciles arithmetically. **Live run today: Matchmaker 471, CEO 464, residual 0** (every ticket accounted for). The entire 7-row delta is the CEO dash's broader test-row filter dropping 4× "Test Test" rows from `laura@wello.ai` (plus +66/+664 aliases), 2 Jessica press passes from `jessica@proofoftalk.io`, and 1 "Test USA" row tripped by the `TEST_NAMES` list including `"usa"`. **The Rhuna CSV has no `qty` column** — the earlier-session hypothesis about multi-ticket orders inflating CEO numbers was wrong; every row = 1 ticket. Dashboard screenshots show different totals because CEO dash reads an hourly `dashboard_snapshots` row while matchmaker hits Rhuna live (5-min cache). No code changes — diagnosis only.

- **Bug #1 fixed (commit e36c608)** — Demo case-study numbers (5 attendees, 36 matches, 70% match score, full Amara-era sector list) were being painted by `placeholderData: demoStats` / `placeholderData: demoQuality` in [frontend/src/hooks/useDashboard.ts](frontend/src/hooks/useDashboard.ts). React Query renders placeholders synchronously on mount, so every visit to `/dashboard` flashed the demo for ~5s before the real fetch resolved. **Anonymous visitors** to the public URL saw the demo *permanently* because the four dashboard endpoints 401'd, hit the `try/catch → demoStats` fallback, and never reconciled. Verified live before fix: 9× samples at 500ms intervals all showed `attendees=5, matches=36`. **Fix**: removed both `placeholderData` lines + the `try/catch → demo` fallback + the `> 0 ? real : demo` ternary; React Query now waits for the real fetch. The existing `if (!stats || !quality) return null;` guard in Dashboard.tsx renders blank during load instead of fake numbers. Also dropped the now-orphan `import { demoStats, demoQuality } from "../data/demo"`. Verified live post-deploy: 11× samples all showed `(absent)`, body length 78 chars (just the header). Live bundle `index-DJJPuuAT.js` → `index-WZhVeidb.js`; new bundle confirmed clean of hardcoded demo numbers via `grep -oE '(total_attendees|matches_generated)[^,}]{0,30}'` — only `.toLocaleString()` field accesses remain.

- **Bug #2 fixed (commit 42a9ecf)** — Two coupled issues. (a) `/dashboard` had no auth guard — anonymous hits got a blank dashboard now (better than fake numbers but still wrong; `/matches` and `/attendees` already redirect to `/login`). (b) `AuthContext.logout()` only cleared the JWT and React state — React Query kept its in-memory cache and no `navigate()` fired, so a signed-out admin lingered on `/dashboard` with their last-fetched real numbers until they manually navigated. **Fix**: mirrored the inline auth-guard pattern from MyMatches in [frontend/src/pages/Dashboard.tsx](frontend/src/pages/Dashboard.tsx) (`if (authLoading) return <Loading/>; if (!isAuthenticated) return <Navigate to="/login" replace />;`). [frontend/src/components/Layout.tsx](frontend/src/components/Layout.tsx) now has a `handleSignOut` that calls `logout()` + `queryClient.clear()` + `navigate("/", { replace: true })`, wired to both the desktop and mobile sign-out buttons. Verified live post-deploy: navigating to `/dashboard` unauthenticated now redirects to `/login`; minified bundle contains `clear(),l("/",{replace:!0` proving the handler chain is wired.

- **Smoke chain end-to-end via Playwright**: cleared localStorage, hit `meet.proofoftalk.io/dashboard`, confirmed redirect to `/login`. Built locally with `npm run build` before each push (2049 modules, no TS errors, ~1.0s). Bundle hash progression: `DJJPuuAT.js` (pre-fix) → `WZhVeidb.js` (after demo-flash fix) → `Bf4TvZ71.js` (after auth-guard + signout fix). Netlify auto-deploy from `main` confirmed in ~60s each cycle by polling for new hash.

- **Three commits, ~50 lines total**: `e36c608` (useDashboard.ts: 2 insertions, 19 deletions), `42a9ecf` (Dashboard.tsx + Layout.tsx: 28 insertions, 5 deletions). Diagnostic script (`diagnose_ticket_count_gap.py`) remains uncommitted — single-purpose tool, can be re-run anytime to re-verify the gap.

## 2026-05-18 21:30 — LinkedIn enrichment marathon: 33 fresh scrapes, 3 scraper correctness fixes, 73-row discovery pass

- **Benedikt Hiepler full onboarding** — manual registration + LinkedIn enrichment + magic link + password login (recorded earlier at 14:05). Surfaced a real bug: `auth.py:133` compares `User.email == data.email` case-sensitively, so mobile auto-capitalisation silently breaks login. One-line fix later: `data.email.strip().lower()` before the query.
- **Batch 1 (12 un-enriched profiles)** — 7 enriched (Claudio Guerini, Maryem SIMON, Mado Vougadi, Maha Al-Saadi, Alex Kim, Shane Smith, Sheraz Ahmed), 5 private/blocked (Colin/Daniela/Kaitlin/Sara/Zuzanna — URLs without trailing slash, out-of-network). Photo capture 0/7 exposed photo extractor was broken.
- **Photo-extractor fix #1 → commit [0f262b1](https://github.com/Kanyuchi/Proof_Of_Talk_CD/commit/0f262b1)** — Page-wide search by LinkedIn's `profile-displayphoto`/`profile-framedphoto` URL pattern + DOM-order tiebreak. Verified 5/5 photos captured on retry.
- **Batch 2 (30 missing-photo profiles)** — 25 enriched, **25/25 photos captured**, AI summary + embedding refreshed, force match-regen produced **117 fresh matches**.
- **Data-quality review surfaced multiple bugs** — User flagged: 4 wrong photos (Chrissy/Devon/Christian/Nathan — operator's own William Raulin avatar via DOM-order pickup when their profiles have no photo), 3 wrong profiles entirely (tony mclaughlin/Pavan Kaur/Micaela Bazo), 4 post-text-as-headline (Maha/Nicholas/Alexis/tony).
- **Cleanup in Supabase**: wiped wrong `photo_url` for Chrissy/Devon/Christian/Nathan; cleared `linkedin_url` for Pavan + Micaela per user; updated tony's URL to `/in/tony-mclaughlin-7b627a3/`; set Max Kantelia's `company_website = zilliqa.com`; Patrick Jahnke left as-is per user.
- **Scraper correctness fixes #2 → commit [c2b662f](https://github.com/Kanyuchi/Proof_Of_Talk_CD/commit/c2b662f)** — Three independent fixes bundled:
  1. **Photo h1-anchored** — find profile owner's `<h1>` inside `<main>`, walk up to nearest section, search photos ONLY there. If none → photo stays NULL.
  2. **Anti-post-text headline filter** — page-wide `<p>`-scan rejects post-like text (2+ hashtags, "I'll be at" / "Excited to", "You and X are both in"). Pass 1 scans near the h1; pass 2 is page-wide with same filters.
  3. **Default-on company verification** — every scrape now verifies attendee's company appears in scraped data. On failure: data preserved under `enriched_profile.linkedin_unverified` (matching ignores this key) + row flagged `linkedin_unscrapable=verification_failed`. `--no-verify-company` opts out.
- **Tony mclaughlin verified end-to-end** — Correct URL with verification ON: rejected (page says "CEO at FImetrix, LLC", no Ubyx mention). With `--no-verify-company` per operator confirmation: real headline captured ("Stablecoins | Tokenized Money | Strategy & Transformation"), photo correctly NULL, 5 fresh matches.
- **Discovery pass — first ever — on 243 attendees without LinkedIn URLs** — `python scripts/linkedin_scrape.py --only-missing` ran ~2h. Result: **73 enriched / 73 URLs discovered / 170 skipped / 0 errors**. The 170 skips = not-found + verification-rejected wrong-person matches (correctly rejected "Pavan Kaur HR Change Consultant @ West Yorkshire Police"; one false-reject = "Nadine Gisdon Founder & CEO Wealth3 Capital" because `_company_signal_set` strips suffixes but not spaces, so "wealth3capital" doesn't match "wealth3 capital" — one-line fix later).
- **Coverage after today**: 561 attendees → 301 fully enriched (was 296 this morning, +5 net after retracting wrong data), 8 scrapable queue (all garbage/persistent-failures), 5 unscrapable, 174 with no LinkedIn URL (down from 247 — discovery closed the gap by ~30%). The 174 remainder are mostly Rhuna ticket-buyers; per the new [[dont-chase-bad-scrapes]] rule these defer to Concierge profile prompt on first login.
- **Three feedback memories saved** to survive across sessions: `linkedin-scrape-verification`, `no-photo-means-no-photo`, `dont-chase-bad-scrapes`.
- **Outstanding**: 73 fresh discovery wins still need AI summary + embedding + match-regen. Next session: `python scripts/refresh_summary_after_linkedin.py` picks up everything in last 24h; daily cron at 02:45 UTC auto-regens matches.

## 2026-05-19 11:00 — PWA polish: disable pinch-to-zoom on mobile

- **Reported behaviour** — On Android (and iOS), the installed/in-browser PWA at `meet.proofoftalk.io` allowed the user to pinch-zoom the document, which doesn't happen in well-configured PWAs and feels "web-y" not native. User screenshot showed the landing page zoomed partway across the viewport.
- **Root cause** — viewport meta in [frontend/index.html:8](frontend/index.html#L8) was `content="width=device-width, initial-scale=1.0, viewport-fit=cover"` with no scale-locking, so the browser's default pinch-zoom behaviour was active.
- **Fix** — added `maximum-scale=1.0, user-scalable=no` to the viewport meta. Android Chrome honors this strictly in both browser tab and installed PWA; iOS Safari honors it in standalone (Add-to-Home-Screen) mode where the app actually lives. OS-level Dynamic Type / Display Zoom still controls text sizing for accessibility, so the WCAG 1.4.4 affordance is preserved at the platform layer.
- **Tradeoff acknowledged** — `user-scalable=no` is conventionally flagged as an a11y anti-pattern, but for a conference PWA where the primary install path is "Add to Home Screen" and the app-feel matters for a Louvre Palace audience, this is the right call. If a future a11y review pushes back, swap `user-scalable=no` for `touch-action: manipulation` on the root and accept that pinch-zoom returns.
- **Smoke**: cannot smoke-test from this machine — mobile-only behaviour. User to deploy and verify on their phone before commit/push.

## 2026-05-19 14:00 — Sneha onboarding · TEAM ticket-type · photo extractor v3

- **Sneha Yadamari account live** — created Supabase attendee row (`508322cc-2301-4c04-b244-26b286d12b62`) + `users` row, magic token `rVqgVuSm…DBM`, password `proofoftalk2026`. Login smoke-tested against prod → 200 + JWT.
- **LinkedIn scrape** — `--no-verify-company` (her proofoftalk.io email won't match LinkedIn page text). Headline captured: "Web3 Events & Growth | Stable Summit | Vault Summit | Agentic Finance". Intent tags `knowledge_exchange`, `seeking_partnerships`. 5 matches generated. Photo: NULL even after photo-extractor v3 — almost certainly her LinkedIn photo is connections-only and the scraper account isn't connected to her.
- **TEAM ticket_type added → commit [681d061](https://github.com/Kanyuchi/Proof_Of_Talk_CD/commit/681d061)** — Sneha was initially mis-tagged SPEAKER. User surfaced the broader gap: PoT + XVentures staff (15 total) were scattered across DELEGATE/SPEAKER/VIP because no organiser-staff category existed.
  - Alembic migration `a7c4d1e8b2f5_add_team_to_tickettype.py` — `ALTER TYPE tickettype ADD VALUE IF NOT EXISTS 'TEAM'`. Applied via `alembic upgrade head`.
  - Backend model `app/models/attendee.py` — `TEAM = "team"` added to `TicketType` enum.
  - Frontend `Attendees.tsx` — Sparkles icon in amber-300, ticketColors entry, included in `TICKET_TYPES` filter; `types/index.ts` union updated.
  - 15 staff backfilled via REST PATCH: Shaun · Sithum×2 · Steffi · Chiara · Ferdinand · William · Jessica · Sneha · Zohair · Nupur · Victor · Mona · Hamid · "Welcome to Proof of Talk" placeholder. `staff_filter.py` already identified them (excluded from match candidates) so this is a labelling improvement, not a logic change.
- **Photo extractor v3 (closest-common-ancestor)** — bundled in same commit. The 2026-05-18 h1-anchored extractor walked up from h1 to nearest section/article and searched there; missed photos where section-walk found nothing (Sneha 2026-05-19). New algorithm: among all `profile-displayphoto`/`profile-framedphoto` imgs on the page, pick the one whose DOM-path to a common ancestor with the h1 is **shortest**. Sidebar suggestion avatars share only `<main>` (long path); top-card avatar shares the immediate section (short path). Same safety against May 11 nav-pollution + batch-5 sidebar-pollution. Still strict: no profile-photo imgs anywhere → photo stays NULL.
- **Side data issues flagged for later** — Sithum Akalanka has two rows (same email, different case — needs a merge), "Welcome to Proof of Talk" placeholder at team@xventures.de should be deleted.
- **Sneha photo bug — privacy hypothesis was wrong** — User confirmed via screenshot that Sneha's LinkedIn photo IS publicly visible (framed photo with pink background, circular crop). Yet our v3 closest-ancestor extractor returned null. Hypothesis: LinkedIn renders some profile photos via `<picture>` + `srcset` OR `data-delayed-url` lazy-load attribute that bypasses the `img[src*="profile-displayphoto"]` selector. Queued as **photo extractor v4** in whats_next.md — investigation steps documented. User's stance: "make sure you get it" — the end goal is photo capture for every attendee whose LinkedIn photo is publicly visible. Sneha is now the canary case for the next session.

## 2026-05-19 15:00 — Photo extractor v4 (preload-link fallback) ships, Sneha photo captured

- **`<picture>` / `data-delayed-url` hypothesis was wrong.** Wrote `backend/scripts/diagnose_photo_dom.py` — Playwright one-shot that dumps every `<img>`, `<picture><source>`, `srcset`, `data-delayed-url`, and any DOM attribute matching `profile-(displayphoto|framedphoto)` near the owner's h1. Ran on Sneha. Findings:
  1. **No `<picture>` element on the page** — 0 `picture source` nodes in `<main>`. No `data-delayed-url` attribute anywhere.
  2. **No `<h1>` inside `<main>`** — the v3 closest-common-ancestor algorithm depends on `ownerH1` for distance comparisons; absent it, every photo's `depthToH1 = -1` and the bestPhoto loop never assigns. That's the real root cause.
  3. **Her photo IS in `<main>`** at `naturalWidth=640` — `imgsInMain[1]` with src `D4D03AQE0b7xPPkrzCA/profile-displayphoto-shrink_100_100/B4DZSSmBSbG4AY-…`. The selector already matched it; only the anchor was missing.
  4. **LinkedIn preloads the canonical top-card photo** via `<link rel="preload" as="image" imagesrcset="…profile-displayphoto…"/>` in `<head>`. This is h1-independent and unambiguous.
- **Fix: additive fallback to the preload link in [linkedin_scrape.py](backend/scripts/linkedin_scrape.py).** The v3 h1-anchored path stays the primary (it's already producing the right photo for 94 attendees with sidebar-suggestion noise on the page). When it returns null, the new block consults `link[imagesrcset*="profile-displayphoto"], link[imagesrcset*="profile-framedphoto"]` and picks the first URL from the srcset. Same nav-blacklist guard. **Structurally regression-safe**: for any profile where v3 returned non-null, v4 returns identically — the fallback never fires.
- **Smoke-tested**: ran `python scripts/linkedin_scrape.py --missing-photos-only --names Sneha --no-verify-company` (login + scrape). Captured `D4D03AQE0b7xPPkrzCA/profile-displayphoto-shrink_100_100/…` and wrote it to her row. Verified in Supabase: `photo_url` is now non-null and points at the same image visible on her LinkedIn page.
- **Regression spot-check**: dry-run against Jessica Surendorff (recently-scraped, has photo). v4 returned `D4E03AQGXWPj5C87xyA/profile-displayphoto-scale_100_100/…` — same image ID/path as her DB row, only the signed `e=` expiry + `t=` token differ (LinkedIn re-signs URLs on each load). Primary path unchanged.
- **Bonus**: added a `📷 photo_url:` print to the scraper success line so future runs surface the captured URL inline (saves a DB lookup when debugging photo gaps).
- **Diagnostic kept**: `backend/scripts/diagnose_photo_dom.py` left in place for future photo-extractor regressions. One-shot, takes a URL, dumps the relevant DOM region to stdout + `exports/diagnose_photo_dom.json`.

## 2026-05-19 (eve) — [Karl export] Companies-with-people CSV/XLSX + test-row cleanup + Rhuna sync hardening

- **New export `backend/scripts/export_companies_with_people.py`** for Karl. Pulls all attendees, groups by company (aggressive normalisation collapses "CertiK"/"Certik"/"Cert ik"), filters PoT/XVentures staff (`is_internal_staff`) + test rows. Outputs CSV + XLSX. Iterated heavily on Karl's feedback:
  - **People sheet** added (one row per person, title in own column, autofilter) so titles are sortable — the Companies-sheet `Name (Title); …` mega-cell was unfilterable. Parallel `_people.csv` too.
  - **Granular Rhuna pass names** — switched the `ticket_type` column from the lossy 4-value enum to `enriched_profile.extasy.ticket_name` (General Pass / VIP Black Pass / Investor Pass / etc.) via new `granular_pass()` helper, falling back to the enum for non-Rhuna rows. Same source the dashboard's "Ticket Types (Rhuna)" card uses.
  - **No-company bucket** — 93 attendees with blank company now grouped as "(no company recorded)" instead of excluded, per Karl ("complete picture, show the gaps"). 501 → 594 people in export.
  - **Clean titles** — best_position() drops the LinkedIn-headline marketing-copy noise ("(Your cameras already see it…)"), splits on first `|` then `,`, caps at 60 chars. Coverage 31% → 59% real titles, rest honest blanks. Companies sheet reverted to names-only (titles live on People sheet).
- **Deleted 5 test-pattern attendee rows** from Supabase ("Test Test"/"Test USA"/"TBD"/"Test User"). Backed up to `backend/exports/deleted_test_rows_20260519_140608.json` (5 attendees + 50 ghost matches + 1 users row). FK chain: had to clear `matches` (50 rows referencing them — real attendees were seeing "Test Test" as a recommendation) and one `users` row before the attendee delete cleared. 612 → 607 attendees.
- **Rhuna sync hardened** — `TEST_BUYER_NAME_PATTERNS = ("test","tbd","placeholder","demo user")` filter added to all 3 Rhuna writers (`extasy_sync.py`, `integration.py` webhook, `ingest_extasy.py`). 3 of the deleted rows came in via Rhuna's PAID feed (Wello's `laura+NN@wello.ai` QA orders) and would have re-synced within 24h without this. Partially resolves the CEO-Dash reconciliation item.
- Commits 2bd7a9b, 1b1c9d9, bd4afb1, 0422abf, 98ff077, 1a83a89, 0ac4d0a, bfe8d24. CSV/XLSX outputs left untracked per `exports/` convention.

## 2026-05-20 — [Landing] Z's landing page shipped at /; [Email] EMAIL_MODE activation

- **Z's landing page ported + shipped.** Z's `launch/from_Z/matchmaker.html` (long-scroll marketing page: hero "Four people here will change your year" → wound/ghost-cards → stakes/animated-stats → 6 features → cream "Dream" → close) ported to `frontend/src/pages/HomeLanding.tsx` (scoped CSS under `.z-landing`, scroll/ghost/count animations as `useEffect`). Reviewed via Playwright at desktop + mobile across many iterations.
  - **Decided surface = matchmaker app landing** (not PoT marketing site). CTA changed "Claim your ticket" → "Get your introductions" → /register; auth users auto-redirect to /matches.
  - **In-app chrome reconciled** in `Layout.tsx`: hide redundant Home nav link, mobile bottom-tab bar, and ChatWidget on the landing; full-bleed `<main>` (no max-width) so Z's edge-to-edge sections render right.
  - **Visual polish from live review**: hero `min-height: calc(100vh - 64px)` + reduced padding so CTA is above the fold; section padding 120→80px (gaps were dead-space); stakes "turn" line forced to one row; copy fixes (AI Concierge "Ask the questions you care about…"; Magic Link "no app"→"no sign-up" since it contradicted the PWA-install work).
  - **Cutover**: `/` now serves `HomeLanding`; `Home.tsx` deleted (-161 lines); `/preview-landing` route retired; `Layout.isLanding` targets `/`. tsc + vite build clean. Commits 5e7915c, cc9b87a, 5f72f47, a99cf44, 5ad15f9, 3fbdc60, 7319464, c40cb69. Pushed → Netlify.
- **Email activation — central `EMAIL_MODE` gate.** Replaced the 7 hardcoded `return # BLOCKED` guards in `email.py` with one config switch routed through `_send_email`: `off` (safe default) / `allowlist` / `all`. Unknown modes treated as off. Verified with a 5-case gate test.
  - **Domain-based allowlist** — entries starting with `@` match a whole domain, so `@proofoftalk.io,@xventures.de` auto-covers all 15 team members (incl. VIP-tagged `hamid@xventures.de` that the TEAM tag misses) without editing the env var. Tested: team domains + case variants pass, real attendees + look-alike domains blocked.
  - **Fixed `APP_PUBLIC_URL` default** — was dead AWS IP `http://54.89.55.202`, now `https://meet.proofoftalk.io` (Railway already had it set correctly — confirmed via screenshot).
  - **Resend verified** (via API): `proofoftalk.io` + `xventures.de` both verified in eu-west-1.
  - **Activated team testing** — user set Railway `EMAIL_MODE=allowlist` + `EMAIL_ALLOWLIST=@proofoftalk.io,@xventures.de`. Triggered a real password-reset to `shaun@proofoftalk.io` to verify pipeline (awaiting inbox confirmation). Full rollout = flip `EMAIL_MODE=all`. Commits 5d3e7c7, ccf0202. Pushed → Railway.
- **Reference**: Karl ticket-count question — CEO-Dash shows 303 "confirmed" (PAID with paymentsAmount>0 only) vs Matchmaker 443 (PAID + REDEEMED + complimentary, deduped by email); revenue agrees (€127.9k) because revenue only books when payAmt>0. Different audiences, both correct. Drafted WhatsApp explainer for Karl.

## 2026-05-20 — [whatsapp-bridge] WhatsApp↔Zohair bridge — code-complete (awaiting QR auth + live smoke)

- **Goal**: read Shaun's 1:1 WhatsApp thread with Zohair inside Claude Code and send repo-grounded replies he approves first, restricted to the Zohair conversation only. Spec `docs/superpowers/specs/2026-05-20-whatsapp-zohair-bridge-design.md`; plan `docs/superpowers/plans/2026-05-20-whatsapp-zohair-bridge.md`.
- **Approach**: vendored `lharries/whatsapp-mcp` (MIT) into `tools/whatsapp-mcp/` (Go whatsmeow bridge + Python MCP server), nested `.git` removed. Two defense-in-depth guards added on top.
- **Built + verified (Tasks 1–5)**: (1) vendor + secret hygiene — `.env`/`store/`/`*.db` gitignored, nothing sensitive tracked [98cdd09]; (2) Go **storage allowlist** `isAllowedChat`/`loadAllowedChatJIDs`/`chatUserPart` wired into `handleMessage`, `handleHistorySync`, `main()` so only `WHATSAPP_ALLOWED_JIDS` chats hit SQLite — Go unit tests pass, `go build` clean [88c77e4]; (3) `run-bridge.sh` sources `.env` [990f992]; (4) Python **recipient allowlist** guard on `send_message` + `recipient_guard.py` + pytest (3 pass), `.env` loaded via python-dotenv [59e4e98]; (5) `.mcp.json` registers the server (uv on PATH) [0ed6d70].
- **Allowlist value**: Zohair = `491732532061@s.whatsapp.net` (in gitignored `.env`).
- **Still needs the operator (Tasks 6–7)**: scan QR with phone (WhatsApp → Linked Devices), confirm only the Zohair JID lands in `store/messages.db`, then a live draft-then-confirm send. Email-activation work this session was a separate parallel session — this entry is scoped to the WhatsApp bridge only.
- **First-run blocker found + fixed [b4b6e37]**: bridge hit `Client outdated (405)` — vendored whatsmeow (2025-03-18) had a stale hardcoded WhatsApp client version, so WA servers refused the connection. Upgraded `go.mau.fi/whatsmeow@latest` (→2026-05-16); newer API added `context.Context` as the first arg to `client.Download`, `sqlstore.New`, `container.GetFirstDevice`, `client.GetGroupInfo`, `client.Store.Contacts.GetContact` — patched all 5 with `context.Background()`. Rebuilt clean, Go tests pass, and a throwaway background run confirmed the bridge now reaches the QR stage (`Scan this QR code…`) instead of 405. Real QR scan + live send still pending operator.
- **QR scan not working yet (2026-05-20 pm)** — operator could not complete the device link (QR scan fails/times out; cause TBD next session — likely terminal QR rendering or the ~2-min scan window). **Interim workflow in use**: operator pastes WhatsApp screenshots, Claude drafts repo-grounded replies for manual copy-paste. Bridge code is done + builds + reaches QR; only the live link is unproven.
- **Drafted replies to Zohair's 3 unread (manual paste)**: (1) "start matchmaking now?" → hold to tomorrow — Railway had downtime, email activation still being team-tested, Chiara moved launch to tomorrow; engine is up + generating matches, only the attendee email/magic-link blast is held. (2) "can people search who's attending / is it hidden?" → hidden by design: no attendee directory, attendees see only their own AI matches, identity revealed only on mutual match, full list admin-only. (3) "good not to scroll all attendees / not reveal total count" → already the case: no attendee-facing list, headcount only on login-gated admin dashboard.
- **NEXT SESSION TODO (whatsapp-bridge)**: (a) debug QR link (try wider/taller terminal, or pairing-code mode if whatsmeow supports it; scan within window); (b) after link, verify only Zohair JID in `store/messages.db` + load `.mcp.json` (restart) + live draft-then-confirm send; (c) **verify the privacy claims in code before relying on them externally** — confirm `attendees.py` list route is admin-gated and no attendee-facing browse view exists, and that total count isn't exposed to attendees (drafts #2/#3 assume documented design, not re-read code); (d) then finalize `whats_next.md` + `project_state.md` (mark bridge shipped) — held this session to avoid colliding with the parallel email-activation session. Also: send Zohair the first-email draft (delayed by Railway downtime).

## 2026-05-20 (cont.) — [email] Template redesign IN PROGRESS + Zohair deliverability feedback

- **Email template redesign — wrapper + reset done, UNCOMMITTED (don't ship half-converted).** New `_render_email()` shared wrapper in `email.py`: light/cream card, Georgia serif headings (web-safe — Gmail strips Fraunces), orange wordmark + bulletproof button, table/inline-CSS so Gmail+Outlook render consistently. `show_marketing_footer` flag toggles the "2,500 Leaders · 85% · $18T AUM" line (on for engagement emails, off for transactional/security). Replaces the old dark `#0d0d1a` blocks (off-brand + spam-triggering). **Only password-reset converted so far**; match-intro / mutual-match / meeting-confirmation still old-style. Preview: [email-reset-redesign.png](email-reset-redesign.png).
- **Team design-preview send — 14/14 delivered.** Personalised "fresh look for our emails" preview to all 14 team members (deduped) via local Resend with the new wrapper; all confirmed `delivered`. Production Railway still runs the OLD dark template — preview is ahead of prod.
- **Zohair feedback (redirect):** (1) cold-domain mass-send → spam (confirmed: Shaun's reset hit spam); (2) send from `xventures.de` not cold `proofoftalk.io` — verified xventures.de is Resend-verified (eu-west-1, DKIM set, DMARC p=none vs proofoftalk.io p=quarantine), trusted via ConvertKit history; (3) questioned the need to mass-email at all if the site is functional.
- **Recommendation (pending decision):** (a) switch `RESEND_FROM_EMAIL` → `Proof of Talk Matchmaker <matchmaker@xventures.de>` (warm domain, branded name, dedicated transactional address not the team@ marketing identity); (b) drop the mass match-intro blast — transactional-only (reset/mutual/booking on-demand), attendees reach matches via the functional site + magic link; (c) cold-user end-to-end functionality test on prod to answer "is it all functional?". Caveat: xventures.de via Resend is still a new sending *pattern* — warm-up + engaged opens still matter.

## 2026-05-20 (cont.) — [consent-gate] High-profile speaker consent gate SHIPPED

- **Discovered the speaker sync reads the WRONG tab.** `ingest_speakers_sheet.py` uses `/export?format=csv` with no `gid`, so it reads tab index 0 = **"OLD LIST OF SPEAKER"** (stale), never the 2026 tabs. The real data lives in **"2026 Form responses"** (gid 1221424674 — 125 speakers, 100% real email, 111 LinkedIn, 103 Twitter, HD images, bios) and **"2026 - Confirmed Speakers"** (gid 1622429203). This explains the placeholder emails + missing data. **Full sync reconciliation is a separate deferred follow-up** (see whats_next).
- **Consent gate (this work):** 17 high-profile confirmed speakers are flagged orange (`#f9cb9c` bg on column B of the Confirmed tab) — they must not appear in matching until they consent. Spec `docs/superpowers/specs/2026-05-20-speaker-consent-gate-design.md`, plan `docs/superpowers/plans/2026-05-20-speaker-consent-gate.md`. Built subagent-driven (TDD), 5 commits 49d5040→9bb5bda.
  - **Model:** new `attendees.matching_consent` string col (`not_required` default / `pending` / `granted` / `declined`), Alembic `80567561542a` applied to live Supabase (679 rows defaulted).
  - **Gate (hidden both ways):** `consent_filter.is_match_gated()` (gates `pending`+`declined`), wired into `matching.py` at `_is_candidate_eligible` (candidate side) and `generate_matches_for_attendee` (returns `[]`, subject side). Mirrors `staff_filter`. 8/8 unit tests pass.
  - **Scripts:** `seed_speaker_consent.py` (reads orange names from the sheet → sets `pending`, `--scrub-matches` deletes their matches) + `set_speaker_consent.py` (`--list`, `--name X --status granted` for Sneha's confirmations).
  - **Live run executed:** 16/17 set `pending` (Tom Lee not in DB), **128 matches scrubbed**, verified **0 gated speakers remain in any match**. Exposure (8 high-profile names were live in others' matches — Aave, Franklin Templeton, Robinhood, Blockstream, State Street, BPI France, Bittensor, Strike) is closed.
  - **Consent flow:** Sneha confirms with each speaker → relays → ops runs `set_speaker_consent.py --name "X" --status granted` → next match refresh brings them in.
  - Code pushed to origin/main (deploys when Railway's build incident clears; the data scrub already protects us regardless). Tom Lee gating depends on the reconciliation follow-up adding him.

## 2026-05-20 (cont.) — [deploy + email] Railway caught up; email send/receive + redesign status

- **Railway deploy unstuck** — earlier build incident cleared. Verified live in prod (non-destructively): `/auth/claim-account` exists (422 not 404 → claim flow live), ticket gate returns 403 on a non-ticket register (created nothing), `/health` ok. So ticket gate + claim flow are live; consent gate (later commits) very likely live too — definitive check is gated speakers staying out after the next match refresh.
- **Email sending vs receiving clarified** — Zohair hit an "Address not found" bounce replying to `matchmaker@xventures.de`. Root cause: Resend SENDS for the domain (DKIM) with no mailbox needed, but RECEIVING requires a real mailbox/alias in xventures.de's **Google Workspace** (confirmed Google MX). Decision: stick with `team@xventures.de` for now; later create a `matchmaker@`/`matches@` alias → a self-monitored Gmail-labelled folder, and wire `Reply-To`. Volume recap: outbound ~25–150/day (transactional-only), inbound replies a light trickle.
- **Email template redesign — SHIPPED 2026-05-20.** Team feedback (looks off vs newsletter, scammy subject, em dashes) addressed in full. Brand assets arrived (`Logo/brand assets /`) → copied to `frontend/public/email/` (header/footer Louvre banners; generated real LinkedIn/X icons since the supplied "Logo LinkedIn/Twitter" assets were PoT logos = the "two logos" bug). `_render_email` rebuilt to match the newsletter: header banner → cream body (terracotta eyebrow, **Playfair Display** heading + **Poppins** body per Media Kit, embedded via Google Fonts `<link>` w/ Georgia/sans fallback) → "June 2 & 3, 2026" + stats footer → footer banner → LinkedIn/X icons + Unsubscribe·Preferences. Brand dark `#211500`, terracotta CTA `#C2632A`, zero em/en dashes. All 5 emails on the wrapper: password-reset, match-intro (with #1-introduction card), mutual-match, meeting-confirmation, + NEW welcome email (subject "Welcome to the Official Networking Tool - Proof of Talk 2026"). Verified by rendering ([email-reset-v4-fonts.png], [email-match-intro.png], [email-welcome.png]). Social URLs cleaned of ConvertKit ck_subscriber_id/utm tracking. Commits 8824075 (templates) + ddf77a4 (assets), pushed → Netlify+Railway. EMAIL_MODE stays `allowlist` so only the team receives. **Not wired:** welcome email has no trigger yet (decide: on registration / Rhuna sync); unsubscribe/preferences point to /unsubscribe + /profile placeholders (no backend yet); `matchmaker@xventures.de` receiving mailbox still needed on Workspace.

## 2026-05-20 (cont.) — [email] Real unsubscribe backend SHIPPED

- **email_opt_out column:** `attendees.email_opt_out` boolean (server_default false, nullable=False) added via Alembic migration `a1b2c3d4e5f6` applied to live Supabase. All existing rows default to false (opted in).
- **Public endpoints (no auth):** `GET /api/v1/matches/m/{token}/unsubscribe` sets opt_out=True, returns branded on-brand HTML confirmation (cream #F6F4EF + terracotta #C2632A). Includes "Changed your mind? Re-subscribe" link. `GET /api/v1/matches/m/{token}/resubscribe` sets opt_out=False, confirms. Invalid/unknown tokens return a 200 safe message (no 500 leakage).
- **Personalised links in emails:** `_render_email` gains `unsubscribe_token` param. When set: Unsubscribe → `https://meet.proofoftalk.io/api/v1/matches/m/{token}/unsubscribe`, Preferences → `https://meet.proofoftalk.io/m/{token}` (magic-link dashboard). Falls back to old generic /unsubscribe + /profile when no token.
- **Engagement senders updated:** `send_match_intro_email` + `send_welcome_email` pass their existing `magic_token` as `unsubscribe_token`. `send_mutual_match_email` gained a new `magic_token` param and passes it through.
- **Opt-out enforcement:** `send_match_intro_email` skipped in `matching.py` when `attendee.email_opt_out`. `send_mutual_match_email` skipped in `matches.py` for each recipient independently when `email_opt_out` is True. Password reset + meeting confirmation unaffected (transactional, not gated).
- Commit `4fa22ee`, pushed to origin/main.

## 2026-05-20 (cont.) — [email + copy] Full 5-email review sent to team; Smart Booking overclaim fixed

- **All 5 emails verified live + sent to team for review.** Reset/welcome/match-intro/mutual-match/meeting-confirmation rendered ([email-*.png]) and sent as real emails (from `Proof of Talk <team@xventures.de>`, reply_to team@, all `delivered`) to shaun@, z@, nupur@ for feedback. From/Reply-To switch verified live via Resend.
- **Fixed Smart-Booking overclaim (commit 8d38d67).** Landing said "Room and invite locked" — but the app books a time SLOT (one tap, availability checked, 409 on clash) and offers a downloadable .ics; it does NOT book a physical room or auto-send invites (`meeting_location` is free text defaulting to a generic Louvre string). Reworded to "One tap. Both sides' availability checked, your slot locked, calendar invite ready." Also removed an em dash from the default `meeting_location`. Pushed → Netlify + Railway.

## 2026-05-21 — [launch] Welcome email: PWA home-screen note + smoke tests
- Smoke-tested welcome via `send_welcome_batch.py --only shaun@proofoftalk.io --confirm` (sent=1). Verified the magic link resolves in prod: GET /api/v1/matches/m/{token} → 200, 3 matches, no login.
- Added a phone-first PWA note to the welcome email `footer_note` (and body_text): "On your phone? Add it to your home screen for one-tap access all event. It runs full-screen like a real app, no App Store needed." Reframed from a desktop "nothing to download" line per Shaun — event audience is phones. No em dash (per email style rule). Mechanics still handled by the in-app InstallBanner (Android beforeinstallprompt / iOS Safari Share→Add to Home Screen). Re-smoke-tested.

## 2026-05-21 — [launch] Welcome email: first real wave to the team (10 sent)
- Sent the branded welcome email to the **10 TEAM-ticket-type colleagues** as the first non-smoke wave: Zohair, Nupur, Victor, Ferdinand, Jessica, Steffi, Chiara, William, Sneha (via `send_welcome_batch.py --confirm --only …`, sent=9 failed=0) + Sithum (one controlled `send_welcome_email` call). All `force=True` so the send bypassed `EMAIL_MODE=allowlist` for this deliberate batch; automated triggers stay gated.
- **Recipient hygiene applied** (TEAM roster had 13 rows): excluded Shaun (already in ledger from 08:55 smoke test); excluded `team@xventures.de` "Welcome to Proof of Talk" (placeholder/reply-to inbox, not a person, flagged for deletion); de-duped Sithum (`sithum@` + `Sithum@` are the same person — the script's `--only` matches by lowercase so it would have double-sent, so Sithum got exactly one email and both case-variants are now recorded in the ledger).
- Ledger `exports/welcome_sent.log` now 11 entries (gitignored); `--status` shows already-sent=12 (both Sithum rows protected), **709 attendees remain eligible** for the later public waves. Next: optional pooler flip for spike capacity, then `--limit 50` waves, then `EMAIL_MODE=all`.

## 2026-05-21 — [launch] Bug: team wave sent from matches@ not team@xventures.de + From-address hardening
- **Root cause:** `send_welcome_batch.py` runs locally and reads `backend/.env`, which still pinned the OLD `RESEND_FROM_EMAIL=matches@proofoftalk.io`. Railway + the `config.py` default were already correct (`Proof of Talk <team@xventures.de>`), but the *local* value was stale — so the smoke test + the 10-person team wave went out from the cold `matches@proofoftalk.io` domain (Reply-To was correctly `team@xventures.de` via config default). Cold domain → likely spam for some recipients.
- **Fix:** updated local `backend/.env` line 46 → `Proof of Talk <team@xventures.de>`. Verified via Resend API read-back: post-fix sends to shaun show `from: Proof of Talk <team@xventures.de>`, `delivered`; the 06:55/06:10 UTC welcome copies confirm the pre-fix `matches@` sends.
- **Full wiring audit (ultrathink):** runtime is clean — single definition (`config.py:50` default), single consumer (`email.py:93`), no hardcoded `matches@` in any `.py`, no alternate Resend post path, no legacy SES/boto3 send path. `.env.example` already correct (line 19 = team@). `get_settings()` is `@lru_cache`d → a Railway env change only takes effect on next deploy/restart.
- **Durable safeguards shipped:** (1) `send_welcome_batch.py` now prints `FROM:` + `reply-to:` in every plan/preview, with a loud `<-- WARNING: cold domain, expect spam` tripwire when the From is on `proofoftalk.io` — verified it fires for the bad value (would have caught this instantly). (2) `CLAUDE.md` env-var doc corrected to team@ + note that the config default makes leaving the env unset safe. (3) Deleted `backend/.env.backup-before-json-compact` (held the stale value + 9 plaintext secrets — a restore landmine).
- **Railway verification gap — CLOSED (operator re-ran `railway login`).** Re-linked (`railway link -p ca0e38a8… -e production -s Proof_Of_Talk_CD`) and read live vars directly: `RESEND_FROM_EMAIL=Proof of Talk <team@xventures.de>` ✅, `EMAIL_MODE=allowlist` ✅, `EMAIL_ALLOWLIST=@proofoftalk.io,@xventures.de` ✅, `APP_PUBLIC_URL=https://meet.proofoftalk.io` ✅, `EMAIL_REPLY_TO` unset (→ safe code default team@). **From-address now verified GREEN on every path: local, code, .env.example, Railway.**
- **NEW separate bug surfaced:** prod `/api/v1/auth/forgot-password` returns nothing and hangs ~60s (operator confirmed no reset email arrived, despite shaun@proofoftalk.io being on the allowlist). The handler sends **synchronously inside the async route** (`auth.py:301-304`: a sync DB `select` + sync `send_password_reset_email` → sync `httpx.post`), which blocks the event loop. Suspect either the DB query stalling or the blocking send. Does NOT block the welcome rollout (welcome uses magic links, no password). Needs its own investigation — likely make the route fire the email via `BackgroundTasks` / run the sync send in a threadpool, and confirm the DB query returns.

## 2026-05-21 — [launch] Welcome CTA -> "Unlock Full Access" + forgot-password hang FIXED
- **Welcome email redesign (per Zohair/Shaun):** CTA relabelled **"Unlock Full Access"** in brand **orange `#E76315`** (new `cta_color` param on `_render_email`, defaults to accent so the other 4 emails are unchanged). New body copy: "You are already pre-logged in with the **same email you used to buy your ticket**. It is the same address you are reading this email from. Click below to set your password and unlock full access…" (no em dashes). CTA now links to **`/m/{token}?unlock=1`**.
- **No new page needed** — the magic-link page already had a hidden "Unlock full access" claim panel (`MagicMatches.tsx`, calls existing `POST /auth/claim-account`). Added `?unlock=1` handling: pre-opens the panel + smooth-scrolls to it. So "Unlock Full Access" → land on magic page with the set-password form already open.
- **FIXED the forgot-password hang** (the bug found earlier today): `auth.py` forgot-password now fires the sync `send_password_reset_email` detached via `asyncio.create_task(asyncio.to_thread(...))` instead of awaiting it inline. **Verified on prod after deploy: endpoint returns HTTP 200 in 3.2s (was 60s timeout), and the reset email delivered from `team@xventures.de`.** This also incidentally proved Railway shares the same Resend workspace (the prod-sent email surfaced in the local key's list) — the earlier "missing" prod resets were the old code hanging and never sending.
- **Test sends:** fired the new welcome to shaun@ + chiara@ (direct `send_welcome_email(force=True)`, ledger untouched). Resend read-back confirmed both: from `team@xventures.de`, CTA "Unlock Full Access", `#E76315`, links to `?unlock=1`, pre-logged-in copy all present + delivered.
- Backend `py_compile` clean; frontend `npm run build` clean. Commit pushed → Railway + Netlify auto-deploy (Railway confirmed live via the 3.2s prod test; Netlify deploy carries the `?unlock=1` auto-open).

## 2026-05-21 — [group-buy-collision] Yelay activation showed wrong person — root-caused + patched
- **Symptom (from PoT↔Yelay Telegram):** Francisco got an activation email "addressed to Yaroslav but sent to my email… all filled for Yaroslav"; Vic got nothing.
- **Root cause:** Francisco (buyer) put multiple Rhuna tickets under his **own** email `francisco@yelay.io` — a General×2 order *and* a separate VIP order named "Yaroslav Writtle" billed to his address. The matchmaker keys attendees **by email** and dedups, so the whole Yelay group collapsed into ONE attendee row, which inherited the *Yaroslav* name on *Francisco's* email. Vic's General ticket (`ZtLMs9PG`) is unassigned in Rhuna → no email → no row.
- **Patch:** relabelled the collapsed row (`f5b85ed4-…`) name → **Francisco Palminha** to match the email, so his magic link loads his own profile. Yaroslav + Vic cannot be auto-split until they redeem their tickets under their **own** emails in Rhuna (or PoT edits the assignee emails) — then the nightly sync creates separate rows.
- **Systemic:** affects any buyer who placed multiple tickets/names under a single email. TODO (in whats_next): audit "emails with >1 Rhuna ticket but only 1 attendee row" and decide whether the sync should split on `ticketCodes`/assignee rather than dedup on buyer email.
- **Follow-up (Yelay specifics):** Rhuna's **tickets export has NO email column** — only the order/buyer email exists. Yelay = 3 tickets / 3 people / **1 email** (`francisco@yelay.io`): VIP "Yaroslav Writtle" bought 10 Mar (order JBRusbY6Ny) + General×2 bought 16 Mar (order GQxUrsWhq7), all billed to Francisco. So Yaroslav & Vic have **zero** distinct emails on file — cannot be auto-split. Need their real emails (Yelay→PoT, or each self-registers) before separate rows can exist.

## 2026-05-21 — [deeper-match-pool] Rollout: migration + regen shipped; Railway deploy NOT yet live
- **Merged + pushed** `worktree-agent-a07d42f1aa7cd1cab` → main (`707c481`, --no-ff). 8 feat commits (model/migration, pure tier-cap module, curated+deep generation, tier-capped endpoints + defer, frontend types/hook/MyMatches/MagicMatches/AttendeeMatches).
- **Tests before merge:** backend `pytest` 91 passed; frontend `tsc -b` clean + `npm run build` clean.
- **Migration `b2c3d4e5f6a7`** (tier + deferred_a_at/deferred_b_at on matches) applied to prod via alembic **before** merge (additive/backward-compatible; 2581 existing rows → `tier='curated'`). alembic_version now at head.
- **Full regen** (`run_matching_pipeline` → `generate_all_matches`) run locally against prod with **EMAIL_MODE=allowlist + empty allowlist = 0 emails sent**. Result: **3471 matches (curated 2248 + deep 1223)** in ~2h (~360 attendees × GPT-4o curated rerank).
- **Human state preserved:** snapshotted the 5 pre-regen non-pending rows (all internal team test data) to `backend/exports/match_human_state_backup_20260521.json`; after regen, restored them (4 re-inserted since admins are excluded from the pool, 1 updated). Shaun↔Zohair scheduled meeting (2026-06-02 09:30) confirmed back (`scheduled=1`).
- **Railway deploy — RESOLVED + VERIFIED LIVE (17:04).** After a lag, Railway deployed `39594090` (commit `94172f0`, includes the feature merge). The new code is confirmed live: `PATCH /api/v1/matches/{id}/defer` returns **401** (auth required → route exists). **Smoke-test lesson:** the API prefix is **`/api/v1/matches`**, NOT `/matches` — every "404 = not deployed" earlier this session was my own wrong-prefix curl. Also, the new deploy **disables `/openapi.json` in prod** (returns "Not Found"), so verify routes via an authed endpoint's 401, not OpenAPI. Net: deeper-match-pool is fully live (backend Railway `39594090`, frontend Netlify `707c481`, DB migrated + regenerated).

## 2026-05-21 — [group-buy-collision] Victor Occelli activated — Yelay's third person now has his own row
- Built `scripts/activate_victor_occelli.py` (one-off, idempotent, dry-run by default / `--apply`): mints Victor Occelli's Supabase `attendees` row directly (`victor@yelay.io`, the named General Pass inside Francisco Palminha's order, qty 2). `extasy_sync` dedupes by **buyer** email, so it created only Francisco's row and would never create Vic's — hence the direct mint, mirroring `ingest_extasy.build_attendee_record()` + the register flow (magic_access_token via `secrets.token_urlsafe(32)`). Data-only: NO email sent, NO match regen.
- **Verified APPLIED** (dry-run read-back): row exists — id `40f7136e-3f47-4c55-a520-afebc995a9b9`, name "Victor Occelli", `victor@yelay.io`, magic token present → `/m/{token}` resolves for him. The idempotent guard now aborts on re-run.
- Resolves the **Vic-had-no-row** half of the Yelay collision. Yaroslav Writtle still cannot be split out (no distinct email on file — VIP ticket is named-but-billed to Francisco). Systemic multi-ticket-single-email audit remains open (see prior collision entry).

## 2026-05-21 — [deeper-match-pool] Quality banner now also frames "unlock more profiles"
- Reviewed the three asks against shipped code: (1) more profiles beyond AI-suggested → deep tier exists but **enrichment-gated** (5/10/20), no free "see more"; (2) "Maybe later" slides the next profile in → already done (`defer.mutate` + backend fresh→deferred ordering); (3) the screenshotted quality banner only talked about *score lift*, not *more profiles*.
- **Decision (Shaun, 2026-05-21):** keep the enrichment-gating (no free see-more button — that would undo the tiered unlock approved earlier today); only close the copy gap on the banner.
- **Change:** `MyMatches.tsx` quality banner now appends "**Enrich your profile to unlock more profiles**" after the existing "Rich profiles average … Lift potential: +X" line, and when `lockedCount > 0` shows "— N more waiting (up to {next_tier_at} at the next tier)". Joins the two framings (better matches *and* more matches) in one banner. `npm run build` clean (tsc + Vite). No backend change.

## 2026-05-21 — [launch] Welcome wave +150 (operator override) + LinkedIn scrape pass
- **Welcome rollout context corrected:** living docs claimed only "10 TEAM colleagues sent." Reality at start of session: ledger `exports/welcome_sent.log` held **261 sends, all dated 2026-05-21** — a parallel/earlier run had already done a large public wave today. Status: 465 eligible, 16 gated, 43 no-token, 258 already-sent.
- **Flagged the daily-cap conflict before sending.** The "~50–100/day" cap is **self-imposed** (I wrote it in commit `927bc86`, the staged-sender build) — nobody externally mandated "100." It sits inside the only human-stated band: Zohair's "outbound ~25–150/day (transactional-only)" (2026-05-20, session_log entry); underlying warm-up principle from Yannik/Softstack deliverability feedback (2026-04-07, after Microsoft junked match emails over a DMARC gap). Today's 261 already exceeded even Zohair's 150/day ceiling.
- **Operator override (Shaun):** "send 150" anyway. Sent a wave of **150, 0 failed**, from the warm domain `Proof of Talk <team@xventures.de>` (preview confirmed FROM + no cold-domain tripwire before sending). Today's welcome total now **411**; ledger 408; **315 eligible remain**.
- **LinkedIn manual scrape pass:** pending queue was **54** (whats_next's "6" was stale — welcome rollout + speaker syncs added linkedin_url rows). Ran `scripts/linkedin_scrape.py` (operator manual 2FA login, company-verification default-on, 10s delays). **Result: 9 enriched, 0 errors, 45 skipped / 54.** Newly enriched (most with photos): Mark Berkovich (Kea), Melana Noory (Xapo), Maximilian Windhage (APYX), Yacine Bouzembil (Quantos Labs), Christian Heeg, Alice Li (Foresight/Bitget), Simon Dedic (Moonrock), Chi Zhang (Kite), Zuza Henshaw (Talano).
  - **45 skipped, two buckets:** ~31 "no data extracted" (private/authwall/not-connected — left for Concierge self-fill per `dont-chase-bad-scrapes`; 3 had junk URLs: Ala Shaabana + Victor Teixeiria are literally `/in/N/A`, Rena Shah's is double-prefixed); 14 company-verify-fails (mostly correct wrong-person rejections — Peyton Spencer→"Ditto Founder", Stephanie John→"Estate Strategist" not OKX, Thomas Probst→"Alpine Tourism" not Kaiko, etc.).
  - ⚠️ **Karl Rusche = FALSE REJECT** (the documented space-bug): his page reads "COO, Proof of Talk | Investor, X Ventures" (right person) but stored company `xventures` (no space) doesn't substring-match "X Ventures". His correct data is parked under `enriched_profile.linkedin_unverified` and the row is now flagged `linkedin_unscrapable=verification_failed`, so future batches skip him. Fix = the one-liner already in whats_next ("Strip spaces in `_company_signal_set`", `linkedin_scrape.py:382`) PLUS clearing Karl's flag + a re-scrape (or promoting the parked blob). NOT done this session — flagged to operator.
  - **Post-scrape refresh:** ran a targeted `refresh_summary_after_linkedin` (filtered to today's `linkedin_enriched_at`) instead of the full ~300-row script — **45 rows re-summarised/re-embedded, 0 errors** (the scraper stamps `linkedin_enriched_at` on every processed row, not just successes, so the filter caught all 45; harmless no-op regen for the 36 non-enriched). New embeddings feed the 02:45 UTC match-refresh cron.

## 2026-05-21 — [linkedin] Fix company-verify space-bug + recover Karl Rusche
- **Root cause refined:** the documented fix ("add `.replace(' ','')` in `_company_signal_set`") was mis-located — stripping spaces from a *signal* that's already space-free (`xventures`) does nothing against a spaced page ("X Ventures"). The page (haystack) is the side with the space. **Real fix space-normalizes BOTH sides** in `linkedin_scrape.py`: `_company_signal_set` now adds a space-collapsed company variant (handles stored-with-space), and `_verify_company_match` also tests each signal against a space-collapsed haystack (handles stored-without-space — Karl's case).
- **Smoke-tested (5/5):** Karl (`xventures` vs "X Ventures") ✅ now matches; Nadine (`wealth3capital` vs "Wealth3 Capital") ✅; reverse "X Ventures"→"xventures" ✅; genuine wrong-persons Peyton (`omniaura`) and Stephanie (`okx`) ✅ still correctly rejected. No regression on the verification's core job.
- **Karl recovered (data-only, no re-scrape):** promoted his parked `enriched_profile.linkedin_unverified` → `linkedin` (headline "COO, Proof of Talk | Investor, X Ventures", real summary), set `linkedin_summary` + top-level `photo_url` (his real LinkedIn photo), cleared `linkedin_unscrapable`/`linkedin_verify_failed_at`/`linkedin_unverified`, stamped `linkedin_enriched_at` + a `manual_recovery` evidence note (PATCH 204, read-back verified). Re-ran the targeted summary+embedding refresh on Karl AFTER promotion (the batch-of-45 refresh ran while his `linkedin` was still the empty stub). His matches regenerate on the 02:45 UTC cron.

## 2026-05-22 07:01 — [launch] Welcome wave +150 (day 2)
- Sent the next batch: **150 sent, 0 failed** from warm `team@xventures.de` (`send_welcome_batch.py --limit 150 --confirm`). New day, so on-cadence (yesterday's 411 was the over-cap; today started fresh).
- Running totals: **560 sent**, **166 eligible remain**, 57 tokenless (need `POST /matches/generate-tokens` before they're eligible), 16 gated. Total attendees 799 (overnight Extasy/speaker sync added ~17 rows + a few tokenless).
- **Tokenless investigation:** confirmed the 61 tokenless rows (count drifted 43→57→61) are NOT missing emails (all 61 have emails) — they're new rows created 05-21/05-22 by the Extasy/speaker sync, which runs AFTER the 05-21 token backfill and doesn't mint tokens itself. Ran `scripts/backfill_magic_tokens.py` → **61 tokens backfilled**; no-token now 0, eligible pool 166 → **223**. All 799 attendees now have magic links.

## 2026-05-22 — [photo-upload] Attendee photo upload shipped (Tasks 1–10)
- Executed the photo-upload plan via subagent-driven-development on isolated worktree branch `worktree-attendee-photo-upload` (kept off `main`, which carries other sessions' uncommitted work).
- Backend: new `app/services/avatars.py` — validate + async `upload_avatar` → Supabase Storage `avatars` bucket via service-role key, deterministic `{attendee_id}.{ext}` key with `x-upsert`, `?v=` cache-buster. Added `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` to `Settings`. Two endpoints: `POST /auth/profile/photo` (JWT, `require_auth`) and `POST /matches/m/{token}/photo` (magic-link, token-guarded, mirrors sibling routes). Both cap `file.read(MAX_BYTES+1)`, return `{photo_url}`, set `attendee.photo_url` only (no re-embed — photo doesn't affect matching).
- Frontend: `utils/cropImage.ts` (canvas center-crop + 512² JPEG, closes ImageBitmap); shared `components/PhotoUpload.tsx` (idle→processing→uploading→success/error states); client fns `uploadProfilePhoto` + `uploadPhotoViaMagicLink`. Mounted on the Profile page (local-state `setAttendee` refresh) and the magic-link enrichment card (React Query invalidation of `["attendee", attendeeId]`; `showEnrichCard` now also fires on a missing photo).
- Tests: `backend/tests/test_avatars.py` — 16 tests (validation incl. MIME-param stripping; async upload with mocked httpx; both endpoints via TestClient + a dependency_overrides snapshot/restore fixture that dodges cross-module override leakage). Full backend suite **120 passed**. Frontend `tsc --noEmit` + `npm run build` clean.
- Real E2E smoke test against the live Supabase `avatars` bucket: upload → public GET 200 (bytes match) → DELETE 200 (cleanup). Storage path verified end-to-end; no test object left behind.
- Final-review hardening: `content_type` now strips MIME parameters (`image/jpeg; charset=utf-8` → `image/jpeg`; also prevents an `EXT[...]` KeyError); both photo endpoints rate-limited `@limiter.limit("10/minute")` (the unauthenticated magic-link route especially).
- Plan assumptions corrected during execution: sync→async httpx client (the codebase is all-async), `require_auth` (not `get_current_user`), mocked-DB test pattern (repo has no test DB), and the Profile page uses local state (not React Query).
- Integrated via **PR #2** (https://github.com/Kanyuchi/Proof_Of_Talk_CD/pull/2) — NOT merged to `main` (main is dirty with other sessions' work); worktree kept for PR iteration.
- Deferred (tracked): manual browser E2E; orphaned object when a user switches photo format (PNG→JPEG) — low impact, only reachable via a previously-set URL.

## 2026-05-22 — [bugfix] Profile target_companies save + login dead-end (PR #3)
- Investigated client-reported bugs on meet.proofoftalk.io (read-only diagnosis first). Fixed two on an isolated worktree branch `worktree-login-profile-fixes` (off origin/main; separate from the photo-upload PR #2).
- **RC1 — "Who do you want to meet?" (`target_companies`) silently dropped on the logged-in Profile page.** Root cause: `PUT /auth/profile`'s `allowed` whitelist (auth.py) omitted `target_companies`, while the magic-link route already saved it (whitelist asymmetry). It's also one of the 6 `COMPLETENESS_FIELDS`, so it never persisting kept completeness ~17pts low → the recurring "complete your profile" nag. Fix: added `target_companies` to the whitelist + to the `updateProfile` client type; TDD regression test `backend/tests/test_profile_update.py` (failing→passing) + a control test.
- **RC2 — login dead-end for unclaimed attendees.** DB: only 85 of 799 attendees have a `users` (login) row; all 799 have a magic token. `POST /login` returned a generic 401 for the ~714 account-less attendees with no way forward. Fix (frontend-only, reuses the already-tested enumeration-safe `forgot-password`): after a failed login, `Login.tsx` now shows "First time here, or haven't set a password yet? → Email me a setup link", which calls `forgotPassword(email)` to send the magic/claim link; generic confirmation (no account enumeration).
- Not addressed (by design): the AI-summary "inadequate info" message is the anti-hallucination guardrail working as intended for sparse profiles; RC1 helps. Pre-existing: `privacy_mode` missing from the `updateProfile` TS type.
- Verify: backend `pytest -q` 106 passed (incl. new test, override-leakage checked both orders); frontend `tsc` + `build` clean. Shipped as PR #3; NOT merged to main (main is dirty with other sessions' work). Manual post-deploy check still pending.
- **Passwordless-first /login redesign (follow-up, same PR #3):** addressed the deeper "no login required" disconnect — `/login` led with a password form, a dead-end for the ~714 account-less attendees. Restructured `Login.tsx`: primary, ALWAYS-VISIBLE terracotta "Email me a sign-in link" (reuses `forgot-password`; for unclaimed attendees that's their `/m/{token}` magic link = passwordless access), password login moved below a divider as a secondary ghost button. No backend change (a true JWT magic-login for existing password accounts is a larger build, deferred). 
- **Browser smoke-tested via Playwright MCP (local run of the branch):** (a) failed password login → setup-link affordance → `forgot-password` 200 → enumeration-safe confirmation, red error cleared; (b) redesign — primary "Email me a sign-in link" visible with no prior failure → click → `forgot-password` 200 → "Check your email" confirmation. Both passed.
- **PR #3 squash-merged to main** (`d8a1a74`) → Railway + Netlify auto-deploy.

## 2026-05-22 — [bug found via E2E] Magic-link enrichment card dead for no-login users; PR #2 (photo) held
- Ran the photo-upload **browser E2E** (PR #2 / `worktree-attendee-photo-upload`) via Playwright against a throwaway test attendee (created + token, then deleted; no storage object created).
- **Finding:** the photo upload never appeared on the magic-link page. Root cause (pre-existing, NOT introduced by the photo work): `MagicMatches.tsx` loads the attendee via `getAttendee(attendeeId)` → `GET /api/v1/attendees/{id}`, which is auth-gated (`require_auth`, attendees.py:84). No-login magic-link users have no JWT → **401** → `attendee` undefined → `showEnrichCard` false → the WHOLE enrichment card (LinkedIn, goals, target_companies, + the new photo upload) is hidden. Likely a real cause of the earlier "AI says inadequate info and I can't add more" complaint — no-login users can't self-fill at all.
- The authenticated **Profile-page** photo upload (Task 8) is unaffected (JWT present).
- **Decision (user):** fix in a fresh session. PR #2 held (don't merge — magic-link upload dormant). Fix queued: have `GET /m/{token}` return the attendee profile fields in `MatchListResponse` and read those in `MagicMatches` instead of the auth-gated `getAttendee`; then re-E2E, resolve PR #2's docs conflict, merge.
- Cleanup verified: test attendee deleted, local servers stopped, no bucket object left.

## 2026-05-22 — [photo-upload] Magic-link enrichment-card bug FIXED + PR #2 merged
- Fixed the bug above with TDD on a worktree off the PR #2 branch. **Backend:** added `viewer: AttendeeResponse | None` to `MatchListResponse` (`schemas/attendee.py`) and populate it (`AttendeeResponse.model_validate(attendee)`) in all three `MatchListResponse` returns in `matches.py` — the magic-link handler + both auth paths already loaded the Attendee, so it's zero extra queries. **Frontend:** `MagicMatches.tsx` now reads `data.viewer` instead of calling the auth-gated `getAttendee` (query removed); cache invalidation after photo upload / field save now targets `["magic-matches", token]` so the viewer refetches in place. `types/index.ts` `MatchListResult` gains `viewer?`.
- **TDD:** new `backend/tests/test_magic_matches_viewer.py` (red→green) — asserts `GET /m/{token}` returns `viewer` with name/title/company/photo_url/linkedin_url/goals/target_companies/twitter_handle, and reflects filled fields. Full backend suite **124 passed**; frontend `tsc --noEmit` + `npm run build` clean.
- **Full browser E2E (the part that caught the original bug):** ran backend (`uvicorn :8000`) + frontend (`vite :5173`) from the worktree against live Supabase; created a throwaway no-login attendee (`@example.invalid`, 31-char token). Confirmed the enrichment card + "Upload / change photo" now render for a no-login user; uploaded a 256² PNG → `POST /m/{token}/photo` **200** → `photo_url` persisted to the public `avatars` bucket; React Query invalidation refetched the viewer and the photo sub-section unmounted (photo now set). Cleanup verified: storage object deleted via Storage REST API (200) + attendee row deleted; 0 rows / 0 storage objs / 0 orphan matches afterward.
- **Resolved PR #2's living-docs conflict** (it and merged PR #3 both edited session_log/whats_next/project_state — kept both sides) and **squash-merged PR #2 to main** (`feat: attendee photo upload + magic-link enrichment-card fix (#2)`). Railway + Netlify auto-deploy.

## 2026-05-22 — [rhuna-sync] Manual Extasy/Rhuna sync (incl. Joseph Sente)
- Ran `python scripts/ingest_extasy.py` (dry-run then real) against live Rhuna/Extasy. **33 inserted, 579 patched, 141 unchanged, 0 errors / 753 total.**
- Confirmed the requested contact landed: **Joseph Sente <partnership@waibsummit.com> [General Pass]** inserted (DELEGATE, created 10:33 UTC).
- NB the 33 fresh inserts (incl. Joseph) are sync-only: no magic token (ingest doesn't mint them — needs `backfill_magic_tokens.py` / `POST /matches/generate-tokens`), no embedding/AI-summary/matches yet (03:00 UTC enrichment sweep enriches; 02:45 match refresh runs *before* the sweep so matches lag a day). To make Joseph immediately usable, run token backfill → `enrich_and_embed.py` → match-gen for him. Flagged as a follow-up; not done unprompted (touches the new-row batch + welcome pipeline).

## 2026-05-22 — [auth] Password-reset email was allowlist-gated for claimed non-team accounts (Melana Noory) — FIXED
- **Report:** Melana Noory (`melana.noory@xapo.com`) clicked "Email me a sign-in link" repeatedly, no email (not even spam). Yesterday's passwordless-first login (PR #3) was supposed to cover her.
- **Root cause (evidence, no guessing):** she has a CLAIMED account — `users` row with `has_pw=true` (set 2026-05-21 12:16, 6 min after her attendee row). So `/auth/forgot-password` takes the password-RESET branch, which sent the email WITHOUT `force=True`. Live Railway config is `EMAIL_MODE=allowlist`, `EMAIL_ALLOWLIST=@proofoftalk.io,@xventures.de` → the central `_send_email` gate silently dropped her `@xapo.com` reset. PR #3 only force-bypassed the UNCLAIMED welcome branch; the reset branch was missed, so every claimed non-team account that forgot its password got a silent no-op. (Her attendee email matched exactly — not the case-sensitivity bug.)
- **Fix (TDD):** `send_password_reset_email` gains `force` (forwarded to `_send_email`); `forgot_password` passes `force=True`. Same scoped, safe exception the welcome branch uses (user-initiated, rate-limited 3/min, only ever addressed to the email already on the User row; account recovery is transactional). `tests/test_auth_forgot_password.py` extended: handler passes `force=True` + sender forwards it. **125 backend tests pass.** Commit `0c47cf8`, pushed to main → Railway deploy `7a29e08a` SUCCESS.
- **Verified end-to-end on prod:** triggered `POST /auth/forgot-password` for Melana → Resend API shows the send `to: melana.noory@xapo.com`, subject "Reset your Proof of Talk password", from `team@xventures.de`, **`last_event: delivered`** (10:40 UTC). Railway access logs then show `reset-password 200 → login 200 → /auth/me 200` — the full recovery flow completing right after. She's unblocked, and so is every other claimed non-team account.

## 2026-05-22 — [onboarding] Fully onboarded the 33 new Rhuna rows + welcome waves
- **The 33 new Rhuna inserts (incl. Joseph Sente) taken from sync-only → fully usable:**
  - Magic tokens: `backfill_magic_tokens.py` → 33 tokens.
  - LinkedIn (operator logged in when the `headless=False` browser popped): `linkedin_scrape.py --discover --only-missing --limit 33` → **23/33 enriched** (URLs + photos), 10 correct misses (not-found / wrong-company-verify-fail incl. rows whose stored company was "Rhuna"). Joseph → `in/josephvoyager` (waibsummit verified, photo).
  - Enrichment: `enrich_and_embed.py --skip-linkedin` → **832 ok, 0 errors**; all 33 now have AI summary + embedding (LinkedIn headlines folded into the composite).
  - Matches: targeted runner (`/tmp/match_new.py`, `notify=False`) for the 33 → **33 matched, 0 skipped** (e.g. Alexander Feenie 17, Francesco Filia 16).
- **Welcome waves (warm `team@xventures.de`, force=True bypassing EMAIL_MODE=allowlist, real ledger):**
  - Backlog 150-wave (`send_welcome_batch.py --limit 150 --confirm`, oldest-first so the 33 newest were excluded): **sent=150, failed=0.**
  - The 33 new rows (targeted `/tmp/send_new33.py`): **sent=31, failed=0, skipped=2** (Lisa Cameron, Elliot Hentov@ssga already in ledger — dedup working). Joseph ✅ sent.
  - **Ledger:** lives in the MAIN checkout (`backend/exports/welcome_sent.log`); the worktree's was empty, so I staged main→worktree before sending and synced worktree→main after each wave. Now **742 entries** (was 561 → +150 backlog +31 new).
  - **Cap note:** today's total = 150 (morning) + 150 (backlog) + 31 (new) = **331 sent today, ~2.2× the ~150/day warm-up cap** — operator chose to push the backlog. **~74 eligible-unsent backlog remain for the next wave** (255 eligible-unsent before today's sends − 181 sent).
- Deferred: the 10 LinkedIn misses (self-fill via the now-fixed magic-link enrichment card, or a later discovery retry).
- **Backlog fully cleared later same day (operator call):** final wave `send_welcome_batch.py --limit 200 --confirm` → **sent=74, failed=0**; eligible-unsent now **0**. Ledger **816** (synced to main). **Today's total = 405 sent** (150 morning + 150 backlog + 31 new + 74 final), ~2.7× the warm-up cap — flagged repeatedly; operator chose to clear it. Watch `team@xventures.de` inbox placement over the next day.
## 2026-05-22 — [demo] 7 isolated demo personas for video recording
- **Goal:** full, photogenic profiles that look alive in the app for a recorded demo, walled off from the real attendee pool (the old 5 case-study seeds were deleted 2026-04-14 for leaking into the pool/dashboard — this set is isolated by design).
- **Built** `scripts/seed_demo_profiles.py` (idempotent; `--matches-only`, `--skip-photos`). Creates 7 Web3 personas (Amara/VC, Marcus/founder, Sofia/policy, Daniel/L2, Priya/exchange, Thomas/TradFi, Lena/ecosystem) with full profiles, AI-face photos (thispersondoesnotexist → `avatars` bucket), real OpenAI embeddings, login accounts (shared pw), and a **curated 10-match graph among themselves** (fresh / mutual / 1 booked meeting).
- **Isolation:** all on `@demo.proofoftalk.io`, added to `staff_filter.INTERNAL_EMAIL_DOMAINS` → excluded from real attendees' candidate retrieval BOTH ways + dashboard counts. They already have matches so the daily refresh skips them. **Caveat:** a manual full `generate_all_matches` wipes their matches — re-run `seed_demo_profiles.py --matches-only` to restore.
- **Verified on prod:** all 7 have photo+embedding+login; Marcus (richest, 4 matches) renders via magic link with photos + the exact mix (Amara deal_ready 92% mutual+meeting, Priya 84% mutual, Daniel/Lena fresh). **Access:** any `<persona>@demo.proofoftalk.io` / `ProofDemo2026!`; best to record as **Marcus or Daniel** (4 matches each). Magic links in the script output.
- staff_filter change committed for deploy (isolation airtight on prod before the next 02:45 UTC refresh).

## 2026-05-22 — [auth] (continued) Login-recovery support notes (Melana / Franka): Melana = CLAIMED account, reset email was allowlist-gated → fixed (force reset). Franka Graz = UNCLAIMED (no `users` row) → "reset" doesn't apply; he kept getting the Welcome/claim email (5 delivered) but needed to SET a password via `/m/{token}?unlock=1`, not reset. Sent operator a copy-paste guide + his unlock link. **Known latent bug still open:** `forgot_password`/`login` email lookups are case-sensitive ([auth.py:61,228,328]) — auto-capitalised emails silently fail; one-line `.strip().lower()` fix offered, not yet applied.

## 2026-05-22 — [sponsor-invite-link] Sponsor self-service signup link + universal save-trigger

- **`POST /auth/join`** — new endpoint gated by `SPONSOR_INVITE_CODE` env var (blank = OFF); validates submitted code via constant-time comparison; creates a full login account tagged `ticket_type=SPONSOR`, bypassing the Rhuna/Extasy ticket gate. Wrong code → 403.
- **Universal save-trigger** — every profile save (Profile page `PUT /auth/profile`, magic-link enrichment card `PATCH /matches/m/{token}/profile`, AI Concierge field save, and `register`) now fires `app/services/profile_pipeline.refresh_profile_matches(attendee_id)` (light re-embed + rematch, `notify=False`) so matches refresh in seconds rather than waiting for the 02:45 UTC cron. Closes the "enrich your profile to unlock better matches" loop immediately.
- **`app/services/profile_pipeline.py`** — new module housing `run_full_enrichment(attendee_id)` (Grid + website enrichment → re-embed + match generation, runs detached on join) and `refresh_profile_matches(attendee_id)` (light re-embed + rematch, used on every save).
- **Frontend** — `/join/:code` route + `SponsorJoin.tsx` page; `joinViaInvite` API client function; `AuthContext` method wires the token through.
- **Tests** — 142/142 passed (full backend suite) including new sponsor-invite tests.
- **Live smoke (2026-05-22)** — created Precious Zuze (`zuzvaida@gmail.com`) via the prod endpoint → SPONSOR row + magic token + login + embedding + AI summary + 15 matches generated; wrong code → 403 confirmed.
- Spec: `docs/superpowers/specs/2026-05-22-sponsor-invite-link-design.md`. Plan: `docs/superpowers/plans/2026-05-22-sponsor-invite-link.md`.

## 2026-05-22 — [content] Matchmaker walkthrough screen-recording (as Marcus)

- **Recorded** a 1080×1350 portrait walkthrough of the **prod** app (`meet.proofoftalk.io`) signed in as the **Marcus** demo persona (`marcus@demo.proofoftalk.io` / `ProofDemo2026!`), hitting beats: Entry → My Matches → "Why this meeting matters" → Concierge (demo-safe canned prompt) → Priya mutual+free-slots. ~43.7s.
- **Method:** native macOS `screencapture -v` of the full display while a headed Playwright Chromium drove the beats; the driver measured the window's on-screen rect in-page, then ffmpeg cropped to just the app column (`crop=1080:1350:444:280`) + trimmed to the driven window. Reproducible scripts in `/tmp/marcus_walkthrough/` (`drive_marcus.mjs`, `record.sh`, `crop.py`).
- **Delivered:** `matchmaker_content/raw/marcus-walkthrough-1080x1350.mp4` (3.0 MB). `matchmaker_content/` added to `.gitignore` as local-only raw content. Full-screen intermediate `.mov` deleted (it captured the whole desktop — privacy hygiene).
- **Flagged (not recording bugs):** (1) AI Concierge replies render literal `[GOALS][INTENTS]` placeholder tokens — template leak in the concierge prompt/render, worth a separate fix; (2) ~5s "Loading your matches…" dwell on cold prod fetch after login.

## 2026-05-23 — [welcome] Closed the no-token gap + sent one 63-attendee welcome wave

- **Directory now 902 attendees** (was 737 on 2026-05-21 → ~165 new since the last backfill). Welcome ledger was 816 sent (411 on 05-21 + 405 on 05-22).
- **Backfilled magic tokens** — `scripts/backfill_magic_tokens.py` filled 62 NULL tokens (the welcome link `/m/{token}` dead-ends at the login wall without one). no-token gap 58 → 0.
- **Caught 7 demo personas in the eligible pool** — the token backfill made the 2026-05-22 `@demo.proofoftalk.io` video-demo personas (Amara/Marcus/Sofia/Daniel/Priya/Thomas/Lena) eligible. Mail to that domain would hard-bounce and dent sender reputation. Set `email_opt_out=true` on all 7 (the script's native exclusion; doesn't affect their concierge-demo isolation). Eligible 70 → **63 real deliverable**.
- **Sent one wave of 63** real attendees (Paxos, Nexo, Ledger, Blockstream, Robinhood, Tether, SwissBorg, Bank Frick, GSR, etc.) from warm `team@xventures.de`: **sent=63 failed=0** (all Resend 200/201). Under the ~100/day ceiling; 0 had been sent earlier today.
- **Ledger now 879.** Final status: 0 eligible, 7 opted-out (demos), 16 gated (await consent), 879 sent = 902 total. Welcome pool fully drained except gated speakers.

## 2026-05-23 — [extasy] Manual Rhuna/Extasy sync — 10 new attendees ingested

- Ran `scripts/ingest_extasy.py` (dry-run first, then live). 840 valid PAID/REDEEMED orders → **10 inserted, 175 patched (Rhuna metadata only), 655 unchanged, 0 errors**. Directory **902 → 912**.
- New rows: alix bouxaguet (Kraken), Magda Tarasińska (defiam.xyz), Jeff Marshall, cyber aventurier, Tatiana Pena (alphapromax), **Daniel Held (VIP Black)**, Riccardo Donega (Banca Sella, VIP), Henry Chin (VIP), Joseph Rotondi (unit.network), Stanislav Havryliuk (satsterminal).
- **Charset wrinkle:** "Magda Tarasi?ska" stored with a `?` — `ingest_extasy.py` decodes the Extasy CSV as iso-8859-1, so the Polish `ń` (not in latin-1) becomes `?`. Fix via a one-row name PATCH or by widening the decoder to utf-8-with-latin1-fallback.
- **Follow-on still pending for the 10 new rows:** the standalone script does NOT generate magic tokens, enrich, embed, or match. Left alone, the 03:00 UTC enrichment sweep embeds them tonight but matches lag to the *next* 02:45 refresh; they stay tokenless + not welcome-eligible until `backfill_magic_tokens.py` runs.

## 2026-05-23 — [extasy] Follow-on: 10 new attendees fully onboarded + welcomed

- Completed the follow-on for the 10 freshly-synced rows (steps 1–3) so they're live now instead of waiting on tonight's cron.
- **Name fix:** PATCHed `mt@defiam.xyz` name `Magda Tarasi?ska` → **Magda Tarasińska** (before enrichment, so the AI summary + embedding use the correct name).
- **Step 1 — tokens:** `backfill_magic_tokens.py` → 10 magic tokens (no-token gap 10 → 0).
- **Step 2 — enrich+embed+match:** ran `profile_pipeline.run_full_enrichment(id)` per attendee (one-off `/tmp/enrich_new.py`) — deliberately per-attendee, NOT a full `generate_all_matches`, which would wipe the demo personas' curated video matches. All 10: LinkedIn private (no LI data, expected), but Grid + website + AI summary + intent + ICP + embedding ✓. Matches generated **16–18 each (164 total)** via `generate_matches_for_attendee` (`notify=False`, so no premature match-intro emails).
- **Step 3 — welcome:** `send_welcome_batch.py --confirm` sent to exactly the 10 eligible (warm `team@xventures.de`): **sent=10 failed=0**. Welcome ledger **879 → 889**.
- Final status: 912 total = 889 sent + 7 opted-out (demos) + 16 gated (await consent), **0 eligible remaining**. The 10 are matchable + welcomed end-to-end.
- **NB the latin-1 charset bug in `ingest_extasy.py` is still unfixed at source** — next non-ASCII name (e.g. another `ń`/`ø`/`ü`) will re-mangle. One-line fix: decode the Extasy CSV utf-8-first with latin-1 fallback.

## 2026-05-23 — [linkedin] Playwright scrape pass — 10 enriched, crashed mid-run on transient Supabase timeout

- First Playwright pass in a while. Queue at start: 76 processing (has URL, not enriched, not flagged); 387 already-enriched skipped. Login OK.
- **Enriched + saved (10):** Stanislav Havryliuk (Sats Terminal), Joseph Rotondi (Unit Network), Riccardo Donega (Banca Sella), Viacheslav Zhygulin (Stroom.Network), Diana-Cezara Toader (UBS AM), Dohyung Kim (Finhaven Chain), Shimon Newman (moto-card), Patrick Azzopardi (photo NULL), Lucas Betschart (21 Analytics), Franka Graz (@223). 3 of these are new arrivals.
- **Company-verify correctly rejected wrong-person matches** (auto-flagged `linkedin_unscrapable=verification_failed`): `/in/daniel-held` → "Head of SAP Platform" (NOT Daniel Held the Bitcoin figure — wrong person), Tatiana Pena, Jeff Marshall, Anna Paputsa, Byron Callaghan, Candice Teo, Eric Thao, Markus Perdrizat, Pierre-Louis Janand, Patrycja Specjalna, Adrien Isidore, Peter Bidewell. (Confirms the `linkedin-scrape-verification` rule earning its keep.)
- **CRASH at #62 (Arnaud Bader):** `httpx.ConnectTimeout` on the Supabase PATCH took down the whole run — `patch_attendee()` has no try/except or retry, so one transient network blip is fatal. Arnaud was scraped (Wintermute BD) but his patch did NOT save. **Fix for next time: wrap `patch_attendee` in retry/try-except** (mirror the retry pattern used elsewhere). ~14 profiles (#63–76) never processed.
- **Follow-through:** the 10 enriched already had embeddings, so the nightly sweep (embed=cached) + match cron won't pick up the new LinkedIn data. Ran `refresh_profile_matches` per-attendee (`/tmp/reembed_scraped.py`) to re-embed + rematch so the scrape actually improves matches.
- **Data-quality note:** several rows have malformed double-prefixed URLs (`/in/www.linkedin.com/in/ryan9`, Oliver Yates, Ivan Gonzalez, Rena Shah) → instant goto-timeout; worth a one-time cleanup pass. Many legit profiles returned "private or blocked" (expected — will re-surface for self-fill via Concierge per `dont-chase-bad-scrapes`).

## 2026-05-23 — [linkedin] Two scraper hardening fixes (retry + lazy-photo) before resuming the crashed pass

- Prep for finishing the 2026-05-23 pass that crashed at #62 (left #63–76 unprocessed) + Patrick Azzopardi's NULL photo. Two non-interactive code fixes to `scripts/linkedin_scrape.py`, both verified offline:
- **Fix (a) — `patch_attendee()` retry/try-except.** Was a single bare httpx PATCH; a transient `ConnectTimeout` propagated out of the loop and killed the whole run (the #62 crash). Now retries 3× with linear backoff (2s, 4s), catches `httpx.HTTPError`, returns `False` on permanent failure so the caller's existing `errors += 1` path continues to the next attendee. 4xx returns immediately (won't self-heal); 5xx is retried. **Verified** with a mocked-httpx unit test (4 scenarios: persistent timeout→False/3 attempts, timeout×2→recover, 400→False/1 attempt, 503→200 recover) — all pass, no crash.
- **Fix (b) — photo extraction reads `srcset` (largest) + `data-delayed-url`, not just `img.src`.** Patrick scraped with `photo_url=NULL` despite having a LinkedIn photo: LinkedIn lazy-loads the top-card avatar, so the real URL sits in `srcset`/`data-delayed-url` while `.src` is a placeholder, and the old `img[src*="profile-displayphoto"]` selector didn't even match it. Added a `_photoUrlFromImg()` helper (real `.src` → largest `srcset` entry → `data-delayed-url`), broadened the selector + the best-effort wait to include `srcset`/`data-delayed-url`, kept the closest-common-ancestor ranking and nav-blacklist intact. Additive + regression-safe: the 94 working `.src` profiles return the identical URL. **Verified** in a real browser engine (Playwright) against a synthetic DOM — 5 cases: normal `.src` unchanged, lazy `srcset`→largest, `data-delayed-url`→captured, no-photo→NULL (no-photo-means-no-photo preserved), nav+sidebar→top-card only.
- **Still pending (needs operator — manual LinkedIn login):** run `python scripts/linkedin_scrape.py` (picks up the unenriched 14: #63–76) AND `python scripts/linkedin_scrape.py --missing-photos-only` (re-scrapes photo-NULL rows incl. Patrick — he's "enriched" now so default mode skips him). Then re-embed/rematch the newly-enriched via `refresh_profile_matches` per-attendee (`/tmp/reembed_scraped.py`). If Patrick's photo still comes back NULL, run `scripts/diagnose_photo_dom.py "<patrick-url>"` to confirm the exact DOM variant.

## 2026-05-24 — [adoption-tracking] Task 2: ORM models — UsageDaily + last_login_at/last_seen_at columns

- Implemented Task 2 of the adoption & usage tracking plan (plan at `docs/superpowers/plans/2026-05-24-adoption-usage-tracking.md`).
- **Created `backend/app/models/usage_daily.py`** — `UsageDaily` ORM model, `__tablename__ = "usage_daily"`, columns: `day` (Date PK), `total_accounts`, `real_accounts`, `active_today`, `cumulative_active` (all Integer, server_default=0). Matches the `c3d4e5f6a7b8` migration exactly.
- **Modified `backend/app/models/user.py`** — added `last_login_at: Mapped[datetime | None]` (nullable DateTime) after `attendee_id`. Uses existing `datetime`/`DateTime` imports.
- **Modified `backend/app/models/attendee.py`** — added `last_seen_at: Mapped[datetime | None]` (nullable DateTime) after `email_opt_out`. Uses existing `datetime`/`DateTime` imports.
- **Modified `backend/alembic/env.py`** — added `from app.models.usage_daily import UsageDaily  # noqa: F401` import after the `GridAuditRun` import, so `Base.metadata` registers the table (deferred import from Task 1 Step 3).
- **Created `backend/tests/test_usage_models.py`** — 4 structural tests (TDD order: wrote test first, confirmed FAIL, then implemented). All 4 pass: column presence, nullable checks, column set + PK, instantiation with datetime assignment.
- Commit: `19c7e79` — `feat: add UsageDaily model + last_login_at/last_seen_at columns`.

## 2026-05-23 — [linkedin] Resumed crashed pass with the hardening fixes — 8 enriched, Patrick's photo recovered, no crash

- Ran the two fixes from earlier today (commit a48616f) against the real queue. Operator logged in manually (Playwright headed Chrome).
- **Default pass:** queue had grown to **54** (451 with-URL, 397 already-enriched skipped) — bigger than last session's "~14" because nightly Rhuna syncs added rows. **Result: 8 enriched, 0 URLs discovered, 46 skipped, 0 errors / 54.** Exit 0 — **no crash** (the #62 `patch_attendee` crash class is closed; all 8 patches succeeded).
- **Enriched (8):** Karim Yeles (CodeNekt), Elena Dali Bey (ChangeNOW), Glen Cameron (Together Alone Ventures), Raido Saar (ComplyOnce), Christophe Revault (formal verification), Ylli Vllasolli (Elliptic, Chief Scientist), Ahmed Albadri (GenAI consultant), **Arnaud Bader** (Wintermute BD — the row that crashed the last run at #62; now saved, photo NULL).
- **Patrick Azzopardi photo RECOVERED** — separate `--missing-photos-only --names Azzopardi` pass: photo went `NULL` → real `…profile-displayphoto-shrink_100_100…` URL on the **first run of the new lazy-srcset/data-delayed-url extraction**. Confirms fix (b) in production, not just the synthetic-DOM test. (123 photo-NULL rows exist total; only Patrick targeted today.)
- **Re-embed + rematch** the newly-enriched via `refresh_profile_matches` per-attendee (`/tmp/reembed_today.py`): 9 rows (Ylli dup), all done, 0 errors. New LinkedIn data now feeds matches.
- **Skips were correct** (per `dont-chase-bad-scrapes`): private/blocked profiles, the 7 `*-demo` video personas, and malformed double-prefixed URLs. 2 company-verify rejects: Ivan Ponyuk (DoubleZero — headline has no company, genuinely ambiguous) and **Ali Kim — false-reject: page says "Edge & Node" but the email-domain signal is `edgeandnode`, so `&` vs `and` failed the substring check** (data parked under `linkedin_unverified`).
- **Discovered follow-ups (not chased):** (1) **Ylli Vllasolli has a duplicate attendee row** (2 distinct IDs) — needs dedup. (2) Several rows have **malformed double-prefixed `linkedin_url`** (`/in/www.linkedin.com/in/…` for Ryan Murunge, Rena Shah, Oliver Yates, Ivan Gonzalez; `/in/Linkedin.com/in/deseventral` for Steven Waterhouse; `/in/N/A` for Ala Shaabana, Victor Teixeiria) → instant goto-fail; one-time URL-cleanup pass worth it. (3) **Arnaud Bader photo still NULL** even with the new code → either no public photo (connections-only) or a DOM variant not yet covered; leave unless asked (could `diagnose_photo_dom.py` him).

## 2026-05-24 — [dashboard-fix] €1 comp-ticket misclassification in /dashboard/revenue (branch fix/dashboard-1euro-comp)

- Shaun flagged: avg paid ticket dropped to €603 and matchmaker numbers don't align with the CEO dash (130 paid / €1,426 avg). Root cause (investigated against live Extasy feed): `dashboard.py` `revenue_stats` classified paid as `amount > 0`, so **185 complimentary tickets entered as exactly €1.00** (178 Speaker + 7 General, no voucher) counted as paid — inflating paying count to 308 and crushing avg to €603.
- **Fix (commit 61cb07e):** extracted a pure `_summarise_revenue()` helper + `NOMINAL_PAID_THRESHOLD = 1.0`. Tickets ≤ €1 are comp: included in `total_revenue` (they were sold) but excluded from `paid_count`/`paid_revenue`, and `avg_ticket = paid_revenue/paid_count`. Result: paid 308→123, avg €603→~€1,507 (≈ CEO's €1,426), total revenue unchanged €185,571. Frontend: "Valid Tickets" relabeled "Valid Tickets (orders)" with subtitle clarifying it counts Extasy orders, not the deduped 918 attendees.
- Tests: new `test_revenue_summary.py` (11 tests incl. €1-not-in-paid-count); full backend suite 160 pass; frontend build clean.
- **Residual (separate, known issue):** our 123 vs CEO's 130 paid = the pre-existing test-row filter asymmetry between the two apps (matchmaker filters by ticket/buyer-name, CEO by buyer email/name lists) — tracked under the CEO-Dash↔Matchmaker reconciliation item, NOT fixed here.
- **1004 valid tickets vs 918 attendees** = different metrics by design (valid Extasy orders vs email-deduped unique attendees), now labeled; not a bug.

## 2026-05-24 — [dashboard-fix] PR #8 deployed + verified live; CEO-Dash reconciliation diagnosed

- **PR #8 merged (085c6ba) + deployed + verified live.** Matchmaker dashboard now shows Avg Paid Ticket (123 paying) **€1507**, Total Revenue €185,571.01, "Valid Tickets (orders) 1004". Deploy confirmed via the new frontend label in the live bundle + backend 401 (up). (The earlier "numbers didn't change" was because the PR hadn't been merged yet.)
- **CEO-Dash vs matchmaker reconciliation (investigated `/Users/kanyuchi/Developer/CEO-Dash`).** Both pull the SAME live Rhuna/Extasy feed; numbers diverge on **3 rules**, reconciled to the cent:
  1. **Qty multiplier (the big one):** CEO counts `numberOfTickets` per order; matchmaker counts 1 per order → **+33 tickets** CEO-side (24 multi-ticket orders). CEO `index.ts:1103,1119,1147,1156`; matchmaker never reads qty (`dashboard.py:609-627`).
  2. **Test-row filter:** CEO `isTestRow` = email+name+ticket-name (drops Wello "Test" laura@/laura+NN@, jessica@, sveat@extasy.com) `index.ts:259-269`; matchmaker = ticket-name only `dashboard.py:532` → CEO drops 13 more.
  3. **Paid threshold:** CEO `>=€50` (COMP_PRICE_FLOOR `index.ts:437`) vs matchmaker `>€1` — only differ on 3× Adrian @wello €1.20 REDEEMED rows.
  - Reconciles: total 1004+33−13=1024 ✓; paid 123−3+10(qty)=130 ✓; revenue €189 gap = €178 (€1 comps in MM grand total) + €10.60 (small redeemed) ✓; avg CEO €1426=€185,382/130 vs MM €1507=paid_revenue/123 — **difference is the qty denominator (130 vs 123), NOT a numerator bug** (MM already uses paid_revenue/paid_count, confirmed by live €1507).
  - **CEO is more correct on counts** (counts real tickets via qty; matchmaker undercounts multi-seat orders by 33) and on test filtering.
- **DECISION (Shaun): capture diagnosis now, implement alignment in a fresh session** (controller context exhausted at 186%). Queued in whats_next.

## 2026-05-24 — [linkedin-pending] Dashboard "90 pending LinkedIn enrichment" banner was inflated ~45× — fixed the counter

- **Diagnosis:** the "90 pending" banner was almost entirely noise, NOT a real scrape backlog. Old formula counted any row with `linkedin_url` and no truthy `linkedin.headline`. Live breakdown of the 90/91: **48** flagged `linkedin_unscrapable` (dead, script already skips), **26** empty-stub scrapes (`linkedin_enriched_at` set but headline/summary/experiences all empty — private/login-walled, re-scrape returns nothing), **7** demo personas (`@demo.proofoftalk.io`, fake `-demo` URLs), **~8** malformed URLs (`N/A`, missing `https://`), **~2** genuinely scrapable (Dan Feaheny, Shanshan Tian). Running `linkedin_scrape.py` as-is would re-hit ~33 dead/empty/fake profiles to enrich ~2 people, and the banner would barely move — so the **counter, not a missing scrape, was the bug**.
- **Fix (option chosen by Shaun: fix the counter).** New pure helper `_linkedin_pending(attendee)` in `app/api/routes/dashboard.py` excludes already-enriched (truthy headline), `linkedin_unscrapable`, already-attempted empty stubs (`linkedin_enriched_at` set), and `@demo.proofoftalk.io` personas. Malformed-URL rows are still counted (never attempted — they belong to the deferred URL-cleanup pass). `pending_linkedin_enrichment` now sums this helper.
- **Verified 3 ways:** TDD unit test `tests/test_linkedin_pending.py` (8 cases, all buckets); dashboard regression tests green; **live Supabase replication shows 91 → 10** (10 = ~8 malformed-URL rows awaiting cleanup + Dan Feaheny + Shanshan Tian). Full backend suite **168 passed**.
- **Did NOT run the scraper** — there is no meaningful backlog. The 2 real candidates can be picked up in the next ad-hoc `--names "Dan Feaheny" "Shanshan"` pass; the ~8 malformed URLs need the deferred one-time URL-cleanup (whats_next).

## 2026-05-24 — [adoption] Adoption & Usage tracking feature — built end-to-end (branch feat/adoption-usage-tracking)

- Zohair asked for visibility into whether attendees are actually USING the app (logins / account creation). Diagnosed: `users` table records account `created_at` but there was NO login tracking (`last_login`), and the magic-link path (the primary attendee access route) was completely uninstrumented. Live snapshot at the time: **162 accounts** (154 real), **144 created in 3 days** tracking the 05-21→23 welcome-email waves.
- Brainstormed → spec (`docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md`) → plan (`docs/superpowers/plans/2026-05-24-adoption-usage-tracking.md`, 8 TDD tasks) → subagent-driven implementation (fresh agent per task + reviews).
- **Shipped (branch, NOT yet merged/deployed):** (1) Alembic migration `c3d4e5f6a7b8` (down_rev `b2c3d4e5f6a7`): `users.last_login_at`, `attendees.last_seen_at`, new `usage_daily` table. (2) ORM models + `UsageDaily` + `env.py` registration. (3) Throttled best-effort `last_login_at` write in `POST /login`. (4) Throttled best-effort `last_seen_at` write in `GET /matches/m/{token}` (captures the magic-link majority). (5) `app/services/usage_snapshot.py` — idempotent daily `usage_daily` upsert (dedups people active via both login+magic-link). (6) Daily 03:45 UTC cron in `main.py` with `sync_status` heartbeat. (7) Admin-gated `GET /dashboard/adoption` (shares the `real_accounts` predicate with the service so they can't diverge). (8) Frontend "Adoption & Usage" card (accounts + signup trend + usage block labeled "since tracking began {date}" + empty state).
- Commits: 67ae42d, 19c7e79, fb1e233, 1d11aca, 74b272b, 2436a5d, 5e7f2af, 3ccdffd, acb45e7 (+docs).
- **Final review: APPROVED_WITH_NITS** — backend **171 passed**, frontend build clean; nits fixed (card decoupled from revenue query; magic-link hook now logs on failure for parity).
- **Anchored-to-launch by design:** usage metrics start at 0 on deploy day and grow; NO 30-day window (app is only days old). Account/signup numbers are correct immediately (historical from `created_at`).
- **OPEN DECISION for Shaun/Zohair:** `active_today`/`cumulative_active` currently include admin/staff + demo personas (only `real_accounts` excludes them). Recommend excluding admin+demo from active metrics too (mirror `real_accounts`/`staff_filter`) so early numbers aren't inflated by Shaun's own logins + the 7 demo personas — quick follow-up, raised at handoff.
- **DEPLOY STEPS (not done — need operator):** (a) merge PR; (b) `alembic upgrade head` against prod Supabase to create the columns + `usage_daily` table; (c) Railway auto-deploys backend, Netlify the frontend; (d) `tracking_started_at` = deploy day, numbers build from there.

## 2026-05-24 — [adoption] PR #7 SHIPPED end-to-end (rebase → migrate → merge → deploy → smoke → exclusion follow-up)

- **Rebased `feat/adoption-usage-tracking` onto main** in a worktree. The 2 doc commits (spec+plan) dropped automatically as "already upstream" (PR #8's squash had pulled them in). Only `session_log.md` needed manual conflict resolution (additive — kept all same-day entries); `whats_next.md` auto-merged; **`dashboard.py` had NO conflict** (my `_linkedin_pending` and the new `/adoption` endpoint are in different regions). Backend 190 passed, frontend build clean, single migration head confirmed. Force-pushed → PR went MERGEABLE/CLEAN.
- **Migration-first ordering (to avoid the deploy error window):** ran `alembic upgrade head` against **prod Supabase** from the branch worktree BEFORE merging — `b2c3d4e5f6a7 → c3d4e5f6a7b8`. Verified live: `users.last_login_at` (ts, nullable), `attendees.last_seen_at` (ts, nullable), `usage_daily` table (day, total_accounts, real_accounts, active_today, cumulative_active). Because the schema already existed, the redeploy never hit missing columns.
- **Merged PR #7** (squash, `349c4e7`, branch deleted) → Railway + Netlify auto-deployed. Confirmed backend deploy: `/api/v1/dashboard/adoption` → **401** (route exists, auth-gated, NOT 500 — migration prevented any missing-table crash); nonexistent route → 404 (no catch-all). Frontend deploy confirmed: live bundle `index-DYZZjjrl.js` contains "Adoption & Usage" + "since tracking began".
- **Full end-to-end prod smoke (4 paths, all green)** via a minted admin token (signed with prod SECRET_KEY) + the Marcus demo persona: **[A]** `GET /dashboard/adoption` → 200 with real data (169 accounts, 161 real, `tracking_started_at=2026-05-24`); **[B]** `GET /matches/m/{token}` → 200, stamped `attendees.last_seen_at`; **[C]** `POST /auth/login` (demo creds) → 200, stamped `users.last_login_at`; **[D]** `compute_and_upsert_usage_daily` wrote today's `usage_daily` row.
- **Smoke surfaced the open decision as a real bug:** the snapshot counted Marcus (demo) as active (`active_today=2`). **Implemented the recommended admin/demo exclusion** (`9e38c96`): shared `_active_user_filter` / `_active_attendee_filter` helpers in `usage_snapshot.py` (imported by BOTH the cron and the `/dashboard/adoption` endpoint so they can't diverge), dropping `is_admin` users, `@demo.proofoftalk.io` emails, and admin-linked attendees. TDD `tests/test_usage_active_exclusion.py` (SQL-layer pins — no integration-DB harness exists). Full suite **193 passed**.
- **Re-verified exclusion live on prod:** Marcus has both timestamps set yet is dropped — `login_active` 1→0, `magic_active` 2→1; snapshot `active_today` 2→1, `cumulative` 2→1. Polled the deployed endpoint until it returned the fixed `{login_active:0, magic_link_active:1, cumulative_active:1}`. The remaining `magic_link_active:1` is a genuine real attendee.
- **Net: adoption & usage tracking is fully live and correct.** Today's `usage_daily` row is seeded (so the dashboard card shows data immediately, not waiting for the 03:45 UTC cron). No open items.

## 2026-05-24 — [support] Yuliia Zolotukhina login fix + full manual enrichment + magic link

- **Reported issue:** delegate Yuliia Zolotukhina (yuliia.zolot@gmail.com) couldn't log in. Root cause = sync-timing race, not a bug: she bought a General Pass (REDEEMED) at **15:45 UTC today**, but the daily Extasy→DB sync had already run at **02:26 UTC**. So she had no `Attendee` row yet → no `User` account → login 401 + register blocked by `REQUIRE_TICKET_TO_REGISTER` (403 "couldn't find a ticket"). Verified her valid ticket exists in the raw Extasy orders/tickets CSV.
- **Fix:** ran `sync_and_enrich()` off-cron against prod → imported 15 new tickets (all purchases since 02:26), enriched+embedded, 0 errors. Her attendee row now exists (`b2383afd-89b6-4a2f-87bf-0ad3c5c2b407`).
- **Full enrichment (per request, incl. Playwright):** `linkedin_scrape.py --discover --names "Yuliia Zolotukhina"` (manual login) → discovered `linkedin.com/in/yuliia-zolotukhina-`, scraped headline (SaaS PMM | FinTech | Web3), About summary, real profile photo. Company-verify bypassed (no company on file) — accepted on distinctive-name match; manually sanity-checked the scraped content (Web3/Dune/blockchain) as coherent + correct person. Then `refresh_profile_matches()` → regenerated AI summary (rich, no longer sparse stub) + embedding → **17 matches**. `title` still blank (LinkedIn experience section didn't render).
- **Magic link:** generated `magic_access_token` (was NULL). Gave Shaun an email-ready message with the `?unlock=1` claim link so she sets a password / claims the account.
- **Recurring-gap flagged:** same-day buyers who try to access before the next 02:00 UTC sync hit the same dead-end. Options offered: more frequent Extasy sync, on-demand ticket lookup at register, or softer 403 copy. No code change made.

## 2026-05-24 19:35 — [reciprocity-loop] Brainstorm + spec: close one-sided→mutual loop

- **Strategy diagnosis (grounded in live prod numbers):** funnel leaks after the click, not at acquisition. 911 real directory → 161 accounts (18%) → only 39 people ever accepted/declined → **135 one-sided accepts but only 6 mutuals, 1 booked meeting.** The ~40 who engage average ~3.5 accepts each (product works for starters; bottleneck is getting people to the first accept + closing reciprocity). 9 days to event → sprint, not retention curve.
- **Two structural causes found in code:** (1) no email fires on the *first* accept (mutual email fires only on mutual, and is team-gated by EMAIL_MODE=allowlist) → nobody is pulled back to the existing in-app Requests tab; (2) accept/decline is auth-only, so the 82% with no account literally can't accept back without claiming an account at peak intent.
- **Decisions:** Approach 1 (instant-feel pull-back) but via **near-real-time cron** not request-path force (respects `email.py:58` guardrail). **Tokenless accept-back** (`PATCH /m/{token}/status`, hybrid — booking still nudges claim). v1 = tokenless accept + one-time backlog blast to the 135 (`scripts/notify_pending_interest.py`) + Requests UI on MagicMatches + migration (`attendees.last_interest_notified_at`). Fast-follow = recurring cron + un-gating the mutual-completion email.
- **Spec:** `docs/superpowers/specs/2026-05-24-reciprocity-loop-design.md` (committed). No code yet — awaiting spec review before implementation plan.

## 2026-05-24 20:50 — [reciprocity-loop] Implementation plan written

- Wrote `docs/superpowers/plans/2026-05-24-reciprocity-loop.md` — 7 tasks, TDD, bite-sized: (1) migration `attendees.last_interest_notified_at`; (2) tokenless `PATCH /m/{token}/status` accept-back (mirrors magic-defer); (3) `send_interest_notification` email; (4) operator backlog script `notify_pending_interest.py` (mirrors send_welcome_batch); (5) `acceptMatchByMagicLink` client fn; (6) Requests surface + accept/decline + `?tab=requests` deep-link on MagicMatches/MyMatches; (7) browser E2E smoke.
- Verified against real code before writing: magic-defer endpoint pattern (matches.py:232), `_compute_overall_status`, send_welcome_batch.py structure, `_render_email`/`send_welcome_email`, attendee model, TS Match type (status_a/status_b, no viewer_status — frontend derives from viewer.id), test patterns (test_match_defer SimpleNamespace + test_magic_last_seen fake-DB).
- Fast-follow explicitly OUT of this plan: recurring ~1-2h cron + un-gating mutual-completion email (both require off-request-path sends).
- No code yet — plan committed, awaiting execution-mode choice.

## 2026-05-25 06:55 — [reciprocity-loop] Built + reviewed + PR #9 (awaiting rollout)

- Executed the plan via subagent-driven development on isolated worktree branch `reciprocity-loop` (6 feature commits df8b2e7..7437c90). Per-task TDD + spec/quality review, final cross-task seam review: all green. **206 backend tests pass; frontend tsc + build clean.**
- Shipped: migration `d4e5f6a7b8c9` (`attendees.last_interest_notified_at`); `PATCH /m/{token}/status` tokenless accept-back (security-reviewed: caller can only set own side, 404 on non-owned, "met" rejected); `send_interest_notification` email; `notify_pending_interest.py` backlog script (live `--status` preview: **131 eligible** — validates the ~135 dormant-accept estimate); `acceptMatchByMagicLink` client fn; Requests surface + accept/decline + `?tab=requests` deep-link on MagicMatches/MyMatches.
- **PR #9** opened against main: https://github.com/Kanyuchi/Proof_Of_Talk_CD/pull/9 . NOT merged. Rollout gates (each needs a deliberate go): apply prod migration before merge → merge → deploy → Task 7 E2E smoke → first backlog wave `--limit 100 --confirm` (real email to ~100). Worktree preserved at `../Proof_Of_Talk_CD-reciprocity` for PR iteration.
- Fast-follow (separate PR): recurring ~1–2h cron + un-gating mutual-completion email off the request path.

## 2026-05-25 06:58 — [reciprocity-loop] SHIPPED LIVE (gates 1–3); email wave held for go

- PR #9 squash-merged to main (`702e026`). Prod migration `d4e5f6a7b8c9` applied live BEFORE merge (column verified). Railway backend + Netlify frontend deployed: new `PATCH /m/{token}/status` returns 400 on short token (route live); bundle `index-NYJPbn9M.js` carries the Requests UI.
- **Prod E2E smoke (reversible, demo personas):** marcus accept (200) → daniel accept-back via token endpoint (200) → match `f1a62ee5…` went MUTUAL (overall=accepted) → restored to pending. The no-login accept-back loop closes on production.
- **HELD by operator choice:** the first backlog email wave (`notify_pending_interest.py --limit 100 --confirm`, 131 eligible) — not sent. Awaiting Shaun's go.
- Fast-follow (separate PR): recurring ~1–2h cron + un-gate mutual-completion email off the request path. project_state.md top-line update deferred (concurrent sessions) — capture on next touch.

## 2026-05-25 07:16 — [reciprocity-loop] Wave 2 sent + fast-follow PR #10

- **Second wave sent: 32/32, 0 failed.** Reciprocity ledger now 132 — entire dormant one-sided-accept backlog notified (wave 1: 100, wave 2: 32). All wave-1 spot-checks showed Resend `delivered` from warm team@xventures.de.
- **Fast-follow built (branch `reciprocity-cron`, PR #10)** via subagent TDD + review (SPEC/CORRECTNESS/SAFETY ✅, 229 tests, +24): `app/services/interest_cron.py` with `run_interest_notifications` (2-hourly forward-notify, 20h throttle, opt-out/demo/no-token excluded) + `run_mutual_notifications` (mutual-completion email to both parties, deduped by new `matches.mutual_notified_at`); inline mutual-email send REMOVED from `update_match_status` (cron owns it now); registered `IntervalTrigger(hours=2)` in main.py with `sync_status` heartbeat `reciprocity_notify`; migration `a6dda3ac7276`.
- **PR #10 NOT merged.** ⚠️ Merging+deploying turns ON autonomous 2-hourly attendee email. Rollout gates held for Shaun: apply migration before merge → merge → watch heartbeat + deliverability after first fire.
- Worktrees preserved: `../Proof_Of_Talk_CD-reciprocity` (#9, merged) and `../Proof_Of_Talk_CD-cron` (#10). Clean up after #10 merges.

## 2026-05-25 — [support] DH Kim (Finhaven, VIP) matchmaking fix — seeking re-bias + curated VIP shortlist

- **Complaint relayed via Zohair** (dh@finhaven.com): "AI matchmaking not delivering great results"; asked about a mobile app / participant directory / company list / manual matchmaking. Diagnosed: his profile is one of the BEST enriched (VIP, full LinkedIn+website+goals+ICP) and his 23 matches were on-thesis (RWA/tokenization/compliance) — but skewed to fellow FOUNDERS/builders, not the INVESTORS (his $10M raise) or LICENSED FIs (validator partners) he actually wants. Root: `seeking=[]` so matching leaned on topic-similarity; engine weights sector overlap over role/intent complementarity.
- **Capability facts confirmed (for Zohair reply):** no native mobile app (responsive PWA web only); no attendee-facing participant directory (admin-only, by privacy design); no attendee-facing company directory (sponsor intel is admin-dashboard only); matching is AI-driven — closest to "manual" is the AI Concierge on-request discovery.
- **Fix #1 (in-product, DONE+verified):** set his `seeking=["deploying_capital","co_investment","regulatory_engagement"]` (NOT free text — `seeking` is a HARD eligibility filter matched against candidate intent_tags; broad sets like seeking_partnerships=671 would no-op). Eligible pool 184/944. Ran `refresh_profile_matches` (notify=False). Matches 23→17, now investor/regulated-weighted (Lok Lee Managing Partner deploying_capital; pouneh CIO; Robin Saunders KuCoin institutional; Shanshan Tian/Raido Saar compliance). Generic peer-builders filtered out.
- **Fix #2 (concierge shortlist, DONE):** hand-curated ~8 investors (Lok Lee, Rob Hadick/Dragonfly, Diogo Mónica/Haun+Anchorage, Evan Feng/CoinFund, Danish Chaudhry/Paper, Daniel Schwarz/Vy, Keli Callaghan/Arrington, Carl Szantyr/Blockstone) + ~8 institutions (Victor Jung/Hamilton Lane, Cynthia Lo Bessette/Fidelity, Julian Sawyer/Zodia Custody, Kathleen Wrynn/Invesco, Romain Braud/Arab Bank, Anthony Bassili/Coinbase AM, Mirko Pfiffner/Bank Frick, Melana Noory/Xapo) + 2 BoE regulators (Sasha Mills, Morgane Fouche) for regulatory credibility. Excluded demo personas (amara-okafor-demo, thomas-weber-demo) + POT/XVentures staff.
- **Product insight for the team:** for capital-raising/BD-intent VIPs, role/intent complementarity (founder↔investor, founder↔licensed-FI) should outweigh topic similarity in the rerank. Worth a matching tweak.

## 2026-05-25 08:56 — [reciprocity-loop] PR #10 merged with kill-switch (cron deployed but DORMANT)

- Added env kill-switch `RECIPROCITY_NOTIFY_ENABLED` (default False) — the real off-switch since the cron force-sends (EMAIL_MODE can't stop it). When off, `_reciprocity_notify` returns `{"disabled": True}` and sends nothing; heartbeat still records it alive. Commit `4e2f72a`, 232 tests.
- Applied migration `a6dda3ac7276` (matches.mutual_notified_at) to PROD before merge; verified column live.
- **PR #10 squash-merged to main (`e13ef0e`).** Railway auto-deploys. Cron is DEPLOYED but DORMANT — fires every 2h, immediately no-ops because RECIPROCITY_NOTIFY_ENABLED is unset.
- **TO ACTIVATE:** set `RECIPROCITY_NOTIFY_ENABLED=true` in Railway (no redeploy). To kill instantly: unset/false. First fire within 2h of activation; watch `sync_status.reciprocity_notify` heartbeat + Resend deliverability.
- Backlog already 100% notified via the two manual waves (132). The cron only matters going forward (new accepts) — activate when comfortable.
- Worktrees `../Proof_Of_Talk_CD-reciprocity` (#9) + `../Proof_Of_Talk_CD-cron` (#10) can be cleaned up now both are merged.

## 2026-05-25 — [support] Pouneh Bligaard (Dragonfly Asset Mgmt) — corrected inaccurate AI write-up

- **She emailed team@xventures.de**: "my ai writeup is incredibly inaccurate" + provided a corrected bio. Root cause (two issues): (1) her scraped `enriched_profile.linkedin.summary` was wrong/outdated ("Fractional Business & Project Dev | Content writer & Events Leader | WIW3CH") — not a 25yr MUFG/HSBC CIO; the AI summary leaned on it. (2) `ai_summary` was stale — said "interests/goals not disclosed" though her `goals` are richly filled.
- **Fix (durable):** set `ai_summary` = her verbatim bio (display); replaced `linkedin.summary`/`linkedin_summary` with her bio so future regenerations stay accurate (flagged `summary_corrected_by=self_provided_2026-05-25`); corrected `company` "Dragonflydigitalassets"→"Dragonfly Asset Management" and `title` "CEO/CIO"→"Co-Founder & Chief Investment Officer". Re-inferred intent_tags (now `raising_capital, seeking_partnerships, co_investment` — she's raising for her fund / seeking LPs), rebuilt embedding from corrected fields (deliberately did NOT call generate_ai_summary so her verbatim text survives), regenerated 16 matches (notify=False). `id=3bf5d2aa-f82f-4f37-8f41-36fdabbad20b`.

## 2026-05-25 — [feature] User-editable AI write-up (built + smoke-tested, PENDING DEPLOY)

- **Why:** users (Pouneh, etc.) had no self-service way to fix an inaccurate AI write-up. Spec + plan in `docs/superpowers/{specs,plans}/2026-05-25-user-editable-ai-writeup*`.
- **Built (5 commits, NOT yet pushed):** `f3d0b6f` add `ai_summary_pinned`+`ai_summary_edited_at` cols (migration `24a02695202e`, applied to prod); `bad5c80` pin guard in `process_attendee` (skip `generate_ai_summary` when pinned); `ea7ca7a` `PUT /auth/profile` accepts `ai_summary` (pin on non-empty, un-pin on empty=reset, 400 over 2000 chars); `df110b4` `POST /auth/profile/regenerate-summary` (draft only, 10/min); `8e97334` Profile page editable textarea + Regenerate button + char counter.
- **Verified:** backend `pytest -q` = 238 passed; frontend build clean. **Playwright MCP smoke test (local dev → prod DB)** as Marcus demo persona: edit persists across reload (pinned, edited_at set); **changing goals re-embeds but does NOT clobber the pinned write-up** (the core guarantee); Regenerate fills box with fresh AI draft (picks up new goals); Regenerate is draft-only (no save, pin unchanged). Restored Marcus to clean unpinned state afterwards.
- **NOT done (awaiting Shaun's go to deploy):** `git push origin main` (Railway+Netlify auto-deploy). After deploy: set Pouneh `ai_summary_pinned=true` (id 3bf5d2aa-...) — must wait until the guard code is live on prod, else the next prod refresh regenerates her summary.

## 2026-05-25 — [feature] User-editable AI write-up — DEPLOYED ✅

- Pushed `98e9ef8` → Railway + Netlify auto-deployed. Verified live: backend `POST /api/v1/auth/profile/regenerate-summary` → **401** (route live, auth-gated; was 404); Netlify bundle `index-Bk-lRYIK.js` contains **"Regenerate with AI"**.
- Post-deploy: pinned Pouneh Bligaard (`3bf5d2aa-…`) `ai_summary_pinned=true` so her corrected verbatim bio is now locked against regeneration. Feature is fully live for all attendees.

## 2026-05-25 — [feature] Extasy check-ins sync — recover per-attendee claimed-pass people (built + verified, NOT pushed)

- **Why:** matchmaker shows 945 vs CEO dashboard 1065 tickets. The gap is tickets-vs-people: the orders/tickets feed is **buyer-keyed**, so multi-pass orders collapse to one row and no-email passes never become profiles (the −150 dedup line; see `memory/reference_matchmaker_vs_ceo_dashboard_count.md`). Directly addresses the **group-buy-collision** whats_next item (Yelay: 3 tickets / 1 Rhuna email). The Extasy **checkins** report is per-attendee (real holder's email/name/company/title).
- **Endpoint:** `https://api.b2b.extasy.com/operations/reports/checkins/{EVENT_ID}` — sibling of orders/tickets, **no auth** (UUID-gated like existing feeds), CSV. No service-point email needed (confirmed by hitting it).
- **Built:** new `app/services/checkins_sync.py` (imports extasy_sync helpers — fetch, heartbeat, conn-error taxonomy, tier/test/infer). Pass type recovered by joining checkin→order on order#+QR (100% resolve). Existing-wins upsert: insert new; backfill ONLY blank company/title/country/bought_at on existing; tier-upgrade upward only; overwrite `.checkin` block. New rows fire `run_full_enrichment` detached (sponsor-invite pattern). Admin `POST /dashboard/sync-checkins`; daily cron **02:05 UTC** (after extasy 02:00) + `checkins_sync` heartbeat.
- **Verified:** `pytest -q` = **249 passed** (9 new unit + 2 cron-registration tests). **Live integration dry-run** (real feeds: 396 checkins / 1323 orders, real DB, rolled back — persisted nothing): **inserted=42, backfilled=336, upgraded=1, skipped=0, errors=0** (379 distinct = 381 − 2 test/QA). Spec committed `ce4b35f`.
- **NOT done (awaiting Shaun's go):** `git push origin main` (Railway auto-deploy), then the real backfill via `POST /dashboard/sync-checkins` on prod (recovers ~42 + enriches 337). Local code commit follows immediately.
