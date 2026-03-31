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
