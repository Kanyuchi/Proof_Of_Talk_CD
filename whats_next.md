# What's Next — POT Matchmaker

**Original Goal:** Ship a Level 3 XVentures Labs submission — a working, demo-ready AI matchmaking product that proves intelligent (not keyword-based) matching at Proof of Talk 2026 scale. The bar: does it feel like a product a decision-maker would actually use?

---

## Now

1. **Phase 2 — return-visit features** — #1 (Free-slot visibility on match cards) **shipped 2026-05-01**, locally smoke-tested, awaiting Railway deploy. Next up is **#2 mutual-match in-app inbox + alert** ("Marcus also picked you" badge on My Matches nav already exists; need a dedicated inbox surface and the "X new matches since last visit" delta). Email re-enables next week so the email half of #2 already exists, just disabled.
2. **Run the Playwright LinkedIn scraper when queue grows** — dashboard shows pending count + amber banner. After today's cleanup the pending queue is **6** (was 8). Run `cd backend && source .venv/bin/activate && python scripts/linkedin_scrape.py` ad-hoc when count climbs. Weekly Monday 09:00 BST routine `trig_014y5YF5MyAHgVG4CQ2e2c9a` will remind.
3. **Change Extasy sync cadence to every 5h** — now that 2026-04-30 fixes are live, edit `backend/app/main.py:62` from `CronTrigger(hour=2, minute=0)` to `IntervalTrigger(hours=5)` per Karl's request. (Keep speakers/grid/match jobs on daily 02:15/02:30/02:45 — only Extasy needs the higher cadence.) Validate after one cycle that all three downstream jobs still fire correctly.
4. **Add `last_extasy_sync_at` to admin dashboard** — surface the timestamp of the most recent successful sync so silent drift is detectable next time. The April 28 silent-failure incident only surfaced because Karl asked about ticket-holder counts; a "Last sync: Xh ago" indicator would have caught it weeks earlier.
5. **Open platform to attendees** — re-enable emails (remove `return` lines in `email.py` — 7 functions, scheduled for next week), decide on attendee onboarding flow (magic link distribution vs self-registration vs Rhuna webhook auto-create). Pouneh Bligaard already asking via LinkedIn. Blocked on Rhuna webhook go-live (Sveat says next week).
6. **Sponsor intelligence rollout** — 3 pilot reports generated (Zircuit, BitGo, CertiK); internal staff now excluded from candidates; reports run as background jobs (no more 504). Next: Victor reviews and pitches; build Priority boost tier; scale to all 24 sponsors.

## Phase 2 build order — return-visit features (research-validated 2026-05-01)

Strategy: 2-day Web3 conf, ~5 weeks pre-event, optimise for **3-5 quality return visits** per attendee, not DAU. The calendar is the killer return-driver across all major competitors (Brella, Grip, Whova, Bizzabo, Cvent, Hopin, Sched, Swapcard). Email re-enables next week so build assuming mutual-match emails will fire.

**Build in this order — each is independent enough to ship one-by-one:**

1. ✓ **Free-slot visibility on match cards** *(shipped 2026-05-01, awaiting Railway deploy)* — `app/services/slots.py` defines the 27-slot conference grid; `MatchResponse.mutual_free_slots` is populated for mutual matches with no booking yet; `MyMatches` shows up to 4 "Both free at — tap to book" chips above the full slot picker; `PATCH /schedule` returns 409 if either party is double-booked.

2. **Mutual-match in-app inbox + alert** ("Marcus also picked you"). Highest-value re-entry trigger. The mutual-match email already exists (disabled) — add an in-app "Mutual interest" inbox/badge so it works without email too. Includes the small "X new matches since last visit" delta on the matches page.

3. **Pre-event countdown + checklist on the home page** ("Event in 32 days. Profile 80%. Top matches scheduled: 0/5. Threads joined: 0/3"). Combines deadline + progress + identity. No competitor risk; checklist framing is well-proven onboarding pattern.

4. **"Who else is going from your sector"** view (Grip pre-event prospecting pattern). High signal for VCs/founders deciding meeting priorities. We already have `vertical_tags` and `enriched_profile.grid` — this is mostly a new view + filter.

5. **Auto-rebook on cancellation** (Grip/Swapcard). Critical for 2-day events (lost slots = lost ROI). Defer until #1 ships — they share infrastructure.

**Email side (when emails re-enable next week):** add weekly **sector pulse** digest (themed per vertical, "DeFi this week: 7 new attendees, 4 deal-ready signals"). Don't build an in-app surface for it — research showed pulse-style content is an email-only winner.

**Killed from earlier draft:**
- ❌ Profile views counter — no B2B event app surfaces it; surveillance vibes among professional peers about to meet IRL; dead-end engagement (can't act on it without breaking mutual-interest norm). If we want a similar dopamine, reframe as actionable: "X people you haven't reviewed expressed interest" — that's just #2 above.
- ❌ "What changed" with rank movement ("3 climbed, 2 dropped") — exposes scoring volatility, looks arbitrary. Keep only "3 new matches" framing.

**Confirmed anti-patterns (do NOT build):** push notifications (no mobile app), gamification beyond progress bar, social-feed/stories, leaderboards/points, random-attendee chat. Cheap-feeling for a Louvre Palace audience.

**Research sources:** Brella, Grip, Whova, Bizzabo, Cvent Attendee Hub, Hopin/RingCentral, Sched, Swapcard, EventMobi product pages + Mapyourshow on app-adoption timing. Vendor performance claims (Brella's "4x retention", Grip's "300% better recommendations") are marketing-page numbers, treat as directional only.

## Soon

- **2026-05-05 (after 02:30 UTC cron) — backfill Grid + website + LinkedIn for new speakers** — Wait for the nightly Grid audit (02:30 UTC) to sweep the 140 Grid-eligible new speakers, then run `cd backend && source .venv/bin/activate && python scripts/enrich_and_embed.py --skip-linkedin` to fill in any rows the cron didn't reach + scrape websites for those Grid surfaced. Finally run `python scripts/linkedin_scrape.py` (operator-driven, manual LinkedIn login) for the **37 new speakers with linkedin_url set**. Today's targeted enrichment did AI summary + embedding only (zero LinkedIn, zero website, only 7 Grid).
- **Audit 22 suspicious-email speaker rows** — `enriched_profile.suspicious_email_in_sheet` flags rows where the master sheet's email column held a colleague/EA address (e.g. `lplatt@mgroupsc.com` for Steven Goldfeder). Those rows are matchable on placeholder emails today; ops should patch real emails when known. Query: `SELECT name, email, enriched_profile->>'suspicious_email_in_sheet' AS in_sheet FROM attendees WHERE enriched_profile ? 'suspicious_email_in_sheet';`.
- **Delete `app/services/speakers_sync.py`** after one full cron cycle (02:15 UTC tomorrow) confirms `speakers_sheet_sync` runs cleanly. The old service has no remaining callers.
- **Re-run match generation + brief Karl on the 143 new speakers** — once enrichment + match-gen complete (kicked off in this session), the dashboard will show ~3× more SPEAKER/VIP recommendations. Confirm new speakers surface in delegate matches before announcing.
- **Align CEO dashboard with Rhuna** — CEO dash reads from stale Google Sheet, matchmaker reads Extasy live. Talk to Steffie about shared definitions. Optionally point CEO dash at Extasy API directly.
- **Reassigned-ticket attendee onboarding** — 23 reassigned tickets exist on Extasy where the buyer purchased extra passes for colleagues. Decision (2026-04-28): **do not auto-create skeleton attendee rows** — Extasy `tickets.ticketOwners` is too sparse to be useful (often just `"Journalist 1"`, `"Francesco"` first-name-only, `"Steffi Press Pass test"`; no email, no company, no LinkedIn). Auto-creating would pollute the matchmaker with 18+ ghost rows that match no one. Instead: (a) build a buyer-facing flow on the magic-link page — "You bought N tickets, tell us about your N-1 colleagues (name, email, LinkedIn)" and only create rows once the buyer fills real data, or (b) let the colleague self-register on the matchmaking app. Until either path is built, ~23 paying conference attendees remain invisible to the matchmaker by design.
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

- ✓ **Phase 2 #1 — Free-slot visibility on match cards (2026-05-01)** — Backend: `app/services/slots.py` (27 thirty-min slots June 2/3) + `mutual_free_slots(a, b)` helper; `MatchResponse.mutual_free_slots` populated in both `GET /matches/{attendee_id}` and `GET /matches/m/{token}`; `PATCH /schedule` adds 409 conflict check on double-booking. Frontend: `MyMatches` renders up to 4 "Both free at — tap to book" chips above the existing slot picker; one click books; `useScheduleMeeting` invalidates on 409 so stale chips disappear. Brella's signature mechanic, smoke-tested locally (`tsc -b && vite build` clean, slot-helper unit check passes), awaiting Railway deploy.
- ✓ **LinkedIn enrichment redesign (2026-05-01)** — Removed the broken `linkedin-api` library path from `enrichment.py` (LinkedIn 403'd it 2026-04-29 onwards). Made the manual Playwright script (`scripts/linkedin_scrape.py`) the primary tool and made it default to skipping already-enriched attendees. Added `with_linkedin_data` and `pending_linkedin_enrichment` counters to the dashboard with an amber banner pointing to the script. Decoupling LinkedIn from the daily cron means downstream jobs (Grid, match refresh) never block on a manual login.
- ✓ **Daily-sync gap fixes (2026-04-30)** — three issues fixed and locally smoke-tested in one bundle: (1) added 02:45 UTC `_daily_match_refresh()` scheduler job — was missing entirely despite docs claiming it existed; (2) declared `ticket_bought_at` on the `Attendee` ORM and wired `_parse_extasy_dt()` into both insert and backfill paths in `extasy_sync.py` — coverage 81/128 → 128/128; (3) refactored `grid_audit._fetch_attendee_domains()` from REST + service-role-key to SQLAlchemy — eliminates the 401 that zeroed today's audit and removes one secret from Railway. All verified locally before commit.
- ✓ **Ticket holder export for Karl (2026-04-27/28)** — `backend/scripts/export_ticket_holders.py` outputs `exports/ticket_holders_company_position.csv` with name/email/company/position/ticket_type/country/LinkedIn. Position falls back to `enriched_profile.linkedin.headline` when registration title empty (lifts position coverage 15% → 79%). Final CSV: 107 ticket holders, 76% company, 79% position, 86% LinkedIn URL.
- ✓ **Three production extasy_sync bugs fixed locally (2026-04-27/28)** — (1) silent skip on existing rows now backfills `extasy_order_id` always; (2) ORM model now declares `extasy_order_id` + `country_iso3` columns (previously silently ignored on every UPDATE/INSERT); (3) per-row Postgres SAVEPOINT via `db.begin_nested()` prevents one bad row from poisoning the whole batch (was causing 100+ cascading errors and zero inserts every night). Local test: backfilled 26 previously-orphan ticket holders, 0 errors. Supabase ticket-holder count 81 → 107. Awaiting commit + deploy + Railway verification.
- ✓ **Railway CLI installed + linked (2026-04-27)** — `brew install railway`, project linked to `observant-achievement` (the auto-generated Railway codename for POT). Use `railway logs --json --lines 5000` for diagnostics.
- ✓ Rhuna ticket audit (2026-04-24) — `backend/scripts/rhuna_ticket_audit.py` exports per-attendee CSV of Extasy ticket name + paid/free status + voucher code, to answer Ferd's DELEGATE-ticket question. Live Extasy API + Supabase join. 125 valid orders: 76 FREE, 49 PAID (€67,497.64). Deferred: surfacing `extasy_ticket_name` + `is_comped` in the `POT Attendees` sheet (only if Ferd asks).
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
