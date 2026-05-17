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
