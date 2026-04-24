# What's Next — POT Matchmaker

**Original Goal:** Ship a Level 3 XVentures Labs submission — a working, demo-ready AI matchmaking product that proves intelligent (not keyword-based) matching at Proof of Talk 2026 scale. The bar: does it feel like a product a decision-maker would actually use?

---

## Now

1. **Open platform to attendees** — re-enable emails (remove `return` lines in `email.py` — 7 functions), decide on attendee onboarding flow (magic link distribution vs self-registration vs Rhuna webhook auto-create). Pouneh Bligaard already asking via LinkedIn. Blocked on Rhuna webhook go-live (Sveat says next week).
2. **Sponsor intelligence rollout** — 3 pilot reports generated (Zircuit, BitGo, CertiK); internal staff now excluded from candidates; reports run as background jobs (no more 504). Next: Victor reviews and pitches; build Priority boost tier; scale to all 24 sponsors.
3. **Schedule `ingest_extasy.py` on a cron** — script is now idempotent; scheduling it (Railway cron or GitHub Action, hourly) closes the last manual step.
4. **Align CEO dashboard with Rhuna** — CEO dash reads from stale Google Sheet, matchmaker reads Extasy live. Talk to Steffie about shared definitions. Optionally point CEO dash at Extasy API directly.

## Soon

- **AI Meeting Prep Briefs** — generate formal briefing doc per scheduled meeting (partially done via concierge chat)
- **Session Matchmaking** — match attendees to conference sessions based on goals/intent
- **Matchmaking Lunch Algorithm** — group attendees into optimised lunch tables

## Later / Backlog

- Post-event continuation — contact export, LinkedIn prompt, D+7 follow-up nudge email
- Session/content matching — match attendees to sessions based on goals and intent tags
- LinkedIn batch enrichment — run `enrich_and_embed.py` with `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` set to backfill LinkedIn data for all attendees with `linkedin_url`
- Grid normaliser improvements — manually-curated canonical-name dict for edge-case companies (e.g. Theqrl → The QRL). Limited ROI — most unmatched companies genuinely aren't in Grid.
- Delete RDS permanently with final snapshot (currently stopped, auto-restarts in 7 days)
- Email template design — match intro email needs design polish before re-enabling
- Rotate Supabase DB password (exposed in CLI session 2026-04-14)

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
- ✓ Ferd outreach sheet sync (POT Attendees tab) — Supabase → Google Apps Script → Sheet hourly mirror via new read-only `attendees_sync` view. 86 rows syncing, `POT Sync Log` tab recording each run, hourly trigger live. Ferd's outreach team can now check `POT Attendees` before cold-emailing to avoid double-contacting ticket holders.
- ✓ `ingest_extasy.py` insert-or-patch refactor — replaced skip-if-exists with per-field PATCH on Rhuna-authoritative columns (`extasy_order_id`, `extasy_ticket_code`, `extasy_ticket_name`, `phone_number`, `city`, `country_iso3`, `ticket_bought_at`, `ticket_type`). Preserves `enriched_profile`, `interests`, `ai_summary`, `embedding`, `goals`, etc. Backfilled 67 rows (0 errors), moving `extasy_order_id`/`ticket_bought_at`/`extasy_ticket_code` coverage from 3 → 70. Script is now idempotent and safe to schedule.
- ✓ Consolidated POT Attendees + In Funnel flag on all feeder tabs — POT Attendees now combines attendees (86) + nominees (224) into single source of truth with Source column. ARRAYFORMULA-based `In Funnel` column on all outreach tabs (Close network, COLD - T1/T2 T3 VCs, Family Offices, Startups, Accelerators): TRUE (green) = skip, FALSE = safe to contact. Auto-discovers new tabs. Daily trigger at 11 PM. Ferd briefed and handover sent.
- ✓ Deploy AI-inferred matching to Railway — ICP feature live on Railway, 85 attendees backfilled, matches regenerated. Amara↔Marcus canonical case at top.
- ✓ Netlify auto-deploy repaired — GitHub App relinked, verified with `7fd610b` Published
- ✓ Seed profiles removed — 5 case-study seeds + 1 test user deleted from Supabase
- ✓ Duplicate profiles merged — Victor Blas ×2, Shaun ×2, Kathryn Dodds ×2, Pavan Kaur ×2 → 4 pairs merged to canonical records
- ✓ Background job system — `app/services/jobs.py` for long-running admin ops; Grid re-enrich + sponsor reports no longer 504
- ✓ Sponsor intelligence internal exclusion — PoT/XVentures staff filtered from candidate retrieval
- ✓ JSONB mutation tracking fix — `enriched_profile` mutations now persist correctly (was silently dropping)
- ✓ Grid matcher hardened — false-positive stopword filter, null field guards, "announced" status accepted; Ubyx + Vancelian recovered; Atos/MarketX/Spot On Chain false positives cleared
- ✓ Grid coverage audit — 23/85 (27%) confirmed as ceiling via name + URL + email-domain probes; CSV exports at `exports/`
- ✓ All emails disabled — platform not yet open to attendees
- ✓ Revenue aligned with Rhuna — removed custom dedup that dropped Tommi's legitimate second purchase (€599 gap resolved)
- ✓ AWS RDS stopped — final snapshot taken, compute savings ~€12/mo
- ✓ Extasy enum fix — uppercase tickettype values for Supabase compatibility
- ✓ Meeting Prep Brief (Phase 4) — `/m/:token/briefing` page: per-match cards with explanation, talking points, Grid intel, social links, scheduled meetings; print/PDF via window.print(); "View Meeting Prep Brief" button on MagicMatches
- ✓ Contact Export (Phase 6) — "Export Contacts" CSV download on Briefing page: name, title, company, match type, score, LinkedIn, Twitter, website, explanation, talking points
- ✓ Post-event email stubs (Phase 5-6) — morning schedule, D+1 wrap-up, D+7 nudge: function signatures + docstrings in email.py, all blocked. 7 total email functions across full lifecycle, all ready to enable.
- ✓ Attendees page fixes — search no longer matches on ai_summary (was returning all results for "proof of talk"); AI summary clamped to 2 lines; Sponsor filter removed (0 sponsors in attendees table)
- ✓ Live sponsor data — `sponsor_intelligence.py` reads from CEO Dashboard Supabase REST API (37 sponsors from CRM) instead of hardcoded 24-sponsor list. Fallback to hardcoded if env vars missing.
- ✓ AI Concierge anti-hallucination — 7 accuracy rules, source tags ([VERIFIED]/[AI-INFERRED]), data quality scoring, AI summary suppressed for SPARSE profiles
- ✓ Upstream enrichment guardrails — `generate_ai_summary()` returns factual stubs for sparse profiles instead of hallucinations. All 96 summaries regenerated (45 stubs + 51 GPT with guardrails).
- ✓ Category column in POT Attendees — SQL-based classification (Investor/Exchange/Regulator/Startup/Infrastructure/etc.) from intent_tags + offers text. ~80% accurate, Ferd accepted as starting point.
- ✓ Admin profile cleanup — removed admin@pot.demo from attendees table, password reset for both admin accounts
- ✓ LinkedIn enrichment restored — `linkedin-api` library (free, email+password auth) replaces dead Proxycurl + manual Voyager cookies. Wired into both `enrichment.py` (FastAPI service) and `enrich_and_embed.py` (standalone script). Set `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` in `.env` to activate.
- ✓ LinkedIn Playwright discovery — `linkedin_scrape.py --discover` uses LinkedIn's search UI to find profile URLs by name + company for attendees without URLs. Takes 70 profiles from 14 enriched → 70 enriched (60% coverage). Requires manual browser login (handles 2FA). Delay 10s between profiles.
- ✓ Grid URL-fallback — `grid_enrichment.py` now accepts `email_domain` and falls back to URL-contains search when name search misses. Picks up name-mismatch cases (e.g. `GenVentures` → `Generative Ventures`). `backend/scripts/grid_domain_audit.py` audits coverage by domain.
- ✓ Grid added to standalone `enrich_and_embed.py` — previously only FastAPI service ran Grid; now the batch script does too. Grid data feeds into the composite embedding text.
- ✓ Full re-enrichment (2026-04-24) — all 116 attendees processed end-to-end: 60% LinkedIn, 31% Grid, 58% website, 100% AI summary + embedding.
- ✓ Matchmaking UX integration brief for Zohair — `docs/matchmaking-ux-integration.md` + `.docx`; 6-phase attendee timeline, what's built vs needed, critical unlock identified
