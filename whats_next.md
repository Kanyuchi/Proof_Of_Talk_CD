# What's Next — POT Matchmaker

**Original Goal:** Ship a Level 3 XVentures Labs submission — a working, demo-ready AI matchmaking product that proves intelligent (not keyword-based) matching at Proof of Talk 2026 scale. The bar: does it feel like a product a decision-maker would actually use?

---

## Now

1. **Sponsor intelligence rollout** — 3 pilot reports generated (Zircuit, BitGo, CertiK); next: Victor reviews and pitches; build Priority boost tier; scale to all 24 sponsors
2. **Post-purchase email sequence** — Resend is live; build the 4-email sequence (welcome, first matches, weekly digest, final briefing)
3. **Email template design** — refine match intro email body layout, branding, content for production use
4. **Deploy AI-inferred matching to Railway** — code merged locally, 60 attendees backfilled against Supabase, matches regenerated (247 @ avg 0.720); push to main + confirm Railway auto-deploy picks it up

## Soon

- **AI Meeting Prep Briefs** — generate formal briefing doc per scheduled meeting (partially done via concierge chat)
- **Session Matchmaking** — match attendees to conference sessions based on goals/intent
- **Matchmaking Lunch Algorithm** — group attendees into optimised lunch tables

## Later / Backlog

- Supabase migration — company infrastructure preference; migration checklist in `docs/deployment.md`
- Post-event continuation (item #20) — contact export, LinkedIn prompt, D+7 follow-up nudge email
- Session/content matching (item #21) — match attendees to sessions based on goals and intent tags
- Proxycurl batch enrichment — re-run enrichment for all 34 attendees once a funded Proxycurl key is available to improve AI summary depth

## Done ✓

- ✓ URL validation — auto `https://` prepend on blur
- ✓ Fix messaging empty state — explains mutual-accept requirement + shortcut to matches
- ✓ Remove JS prompt on decline — inline textarea panel in both MyMatches + AttendeeMatches
- ✓ Fix meeting scheduling — slot picker for June 2–3, ICS download
- ✓ Success/failure states on all async actions
- ✓ Mobile-responsive UI — 44px touch targets, responsive grids
- ✓ POT brand design — `#E76315` orange, dark bg, heading font
- ✓ Role-based UI — admin-gated Attendees page, attendees see only their own matches
- ✓ In-app messaging — threaded chat on mutual matches
- ✓ Your Schedule timeline — upcoming booked meetings in MyMatches
- ✓ Daily match refresh cron — 02:00 UTC
- ✓ Extasy live pipeline — 21 paid attendees confirmed (34 total in DB); enrichment 34/34; 121 matches at avg 0.69
- ✓ Language fix — "Why this meeting matters" consistent across both match views
- ✓ Action model — full-width dominant "I'd like to meet" CTA; "Maybe later" as text link
- ✓ Saved shortlist — bookmark icon, All/Saved tab filter, localStorage persistence
- ✓ Email service — AWS SES (new matches, mutual match confirmed, meeting scheduled)
- ✓ Reduced registration friction — 9 fields / 3 steps → 4 fields / 1 step
- ✓ Profile photos (item #8) — GDPR decision: no auto-fetch from LinkedIn or third parties; users upload their own photo URL; ui-avatars styled initials always render as fallback
- ✓ OpenAI API key replaced on EC2 — enrichment pipeline fully functional
- ✓ Friday weekly update email (`docs/friday-update-2026-03-20.md`) — team update covering 2026-03-17 → 2026-03-20
- ✓ Matching engine: vertical_tags + intent_tags in embeddings, GPT prompt, and deterministic reranking with COMPLEMENTARY_VERTICALS map
- ✓ AI Concierge: markdown rendering (react-markdown + MarkdownMessage component), formatting instructions in system prompt, vertical_tags in context + sector filter
- ✓ Deploy + re-embed + re-match: 129→140 matches, avg 0.69→0.70, 36 above 0.75; backend on green EC2, frontend on Netlify
- ✓ Supabase sync: 140 matches synced via REST API
- ✓ Smoke test: health, registration, concierge markdown, matches endpoint, frontend bundle all verified
- ✓ Password reset flow — forgot-password + reset-password endpoints, SES email template, frontend pages, "Forgot password?" link on login
- ✓ Deploy to pot-matchmaker — relinked Netlify CLI to XVentures site, deployed frontend to `meet.proofoftalk.io`, updated `deploy/push.sh` with Netlify step
- ✓ Magic link (no-login access) — `magic_access_token` on Attendee, `/m/:token` frontend route, `GET /matches/m/{token}` backend endpoint, auto-gen on registration, email CTA updated
- ✓ Architecture & scale doc — `docs/architecture-scale.md` (KR 3.2)
- ✓ Cost analysis doc — `docs/cost-analysis.md`, €0.39/attendee optimised (KR 3.3)
- ✓ Home page auth-aware — logged-in users see "View your matches" / "Edit your profile"
- ✓ Feature card copy rewrite — non-technical, attendee-facing descriptions
- ✓ Social links on match cards — LinkedIn, Twitter, website icons on MyMatches
- ✓ Investor Heatmap — capital activity by sector on Dashboard (brainstorm Quick Win)
- ✓ QR Business Card Exchange — scannable QR on Profile page linking to magic link (brainstorm Quick Win)
- ✓ Pre-Event Warm-Up Threads — 11 vertical-based group discussion threads, nav link, live polling (brainstorm Quick Win)
- ✓ Vertical tags aligned with 1000 Minds — 12 verticals (incl. privacy), display names, surfaced in frontend (AttendeeMatches, Attendees, MyMatches)
- ✓ Directory cleanup — temp files, .DS_Store, reorganised docs/scripts, consolidated node_modules
- ✓ Runa integration API — 4 endpoints (magic link lookup, ticket webhooks, status), API key auth, spec doc for Swerve
- ✓ The Grid B2B integration — GraphQL enrichment from thegrid.id, verified company data on match cards; active matching via sector→vertical mapping, Grid products in GPT-4o scoring, health check endpoint; API hardened with retries + case-insensitive search
- ✓ Privacy mode — anonymous/pseudonymous B2B-only profiles with reveal-on-mutual-match, profile toggle, email handling
- ✓ Supabase migration — full cutover from RDS to Supabase PostgreSQL; 73 attendees, 317 matches, all tables migrated; IPv4 add-on enabled
- ✓ 1000 Minds speakers sync — speakers_sync.py reads from speakers table, upserts into attendees; daily cron 02:15 UTC; admin dashboard button
- ✓ Mutual match nav badge — orange count badge on My Matches nav when someone accepted you
- ✓ ML feedback loop — GPT-4o ranking prompt includes prior decline reasons as negative examples
- ✓ Match card feedback buttons — ThumbsUp/ThumbsDown for lightweight quality signals
- ✓ Admin match card parity — social links, vertical tags, Grid card now show on admin view too
- ✓ Enhanced dashboard — revenue tracking (€47.6k), registration funnel, weekly growth, attendee sources, profile quality bars; Extasy order deduplication fix
- ✓ QR code in email — CID attachment renders in Gmail; match intro email copy updated
- ✓ "Who do you want to meet?" — target_companies field on Profile + magic link enrichment card
- ✓ Twitter URL fix — handles full URLs (x.com/handle) not just @handle
- ✓ AI-inferred customer matching — GPT-4o infers ICP (`offers`, `ideal_customers[]`, `ideal_partners[]`, `anti_personas`) per attendee; fed into embeddings + ranking prompt + deterministic rerank (+0.03/+0.05 ICP keyword hits, +0.03 two-way ICP fit); company-similarity fallback when no strong matches; backfilled all 60 attendees; 247 matches @ avg 0.720 (up from 0.704); Amara↔Marcus classic case surfaces at 0.820 deal_ready
