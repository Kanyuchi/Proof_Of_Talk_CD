# POT Matchmaker — Status Report for Zohair

**From:** Shaun  
**Date:** 22 April 2026  
**Event:** June 2–3, 2026 — 41 days away

---

## Executive Summary

The AI matchmaking engine is built, deployed, and running against live attendee data. 96 real attendees are in the system with 234 AI-generated matches. The product works end-to-end — from ticket purchase through to meeting scheduling. We're at the stage where the two critical unlocks are: **(1) opening the platform to attendees** (blocked on Rhuna webhook), and **(2) rolling out sponsor intelligence reports** (ready to pilot).

---

## What's Live Today

**meet.proofoftalk.io** — fully deployed on Railway (backend) + Netlify (frontend)

| Capability | Status | Numbers |
|---|---|---|
| 3-stage AI matching (embed → retrieve → rank) | ✅ Live | 234 matches across 96 attendees, avg score 0.713 |
| AI-inferred customer profiling (ICP) | ✅ Live | Who would buy from / invest in / partner with each attendee |
| Magic link access (no login required) | ✅ Live | One-click match briefing via `/m/:token` |
| Meeting prep briefs | ✅ Live | Per-match talking points, Grid intel, social links |
| In-app messaging + meeting scheduling | ✅ Live | Chat on mutual match, June 2–3 slot picker, ICS download |
| Pre-event discussion threads | ✅ Live | 11 sector-based threads |
| QR business card exchange | ✅ Live | Scan → see someone's match dashboard |
| Organiser dashboard | ✅ Live | Revenue, funnel, match quality, attendee sources |
| Sponsor intelligence reports | ✅ Live (pilot) | 3 generated (Zircuit, BitGo, CertiK), 37 sponsors from CRM |
| Ferd's outreach dedup | ✅ Live | Auto-syncs to his Google Sheet, flags ticket holders across all tabs |
| Contact export (CSV) | ✅ Live | Attendees can download their match data |

---

## What We Built vs. The Original Vision

**Original pitch:** "Replace the randomness of conference networking with AI that finds non-obvious, high-value connections."

**Where we landed:**

The matching engine does significantly more than the original pitch. It doesn't just match similar people — it infers each attendee's ideal customer profile, identifies complementary needs, and explains why each meeting matters. The system enriches thin registration data with Grid B2B company intelligence and website scraping to build a complete picture.

**Key innovations beyond the original concept:**
- **ICP-driven matching** — "who would buy from this person?" not just "who is similar"
- **Three match types** — Complementary, Non-Obvious, Deal-Ready (not just one score)
- **Sponsor intelligence** — repurposing the matching pipeline for a revenue product
- **Magic links** — zero-friction attendee access, no account creation needed
- **Anti-hallucination guardrails** — AI summaries are honest about what they don't know

---

## Feedback We've Acted On

| Feedback | From | Action Taken |
|---|---|---|
| "How do we integrate matchmaking into the attendee experience?" | Zohair | Designed 6-phase timeline (Instant → Warm-Up → Prep → At-Event → Post-Event), built magic link onboarding, email lifecycle stubs |
| "I need to know who's already signed up before we cold-email them" | Ferd | Built Supabase → Google Sheet sync with In Funnel flag on all outreach tabs |
| "Can we tell who's an investor vs startup?" | Ferd | Added AI-inferred Category column to POT Attendees (~80% accurate) |
| "Sponsors should be a revenue product" | Brainstorm | Built sponsor intelligence: per-sponsor reports with Grid data + relevant attendees + conversation openers. 3 tiers proposed (€5-50k) |
| "The AI makes things up about attendees" | QA | Added anti-hallucination guardrails at both enrichment (upstream) and concierge (downstream) layers. 45 sparse profiles now get factual stubs instead of fabricated summaries |

---

## Current Blockers

### 1. Opening to Attendees (Critical Path)

The platform is ready but attendees can't access it yet. The bottleneck:

- **Rhuna webhook** — Sveat (Swerve) said "next week" as of April 19. This webhook auto-creates attendee accounts on ticket purchase. Without it, attendees need manual onboarding.
- **Emails disabled** — all 7 email functions have `return` statements preventing sends. Ready to enable once we decide the onboarding flow.
- **Decision needed:** Do we wait for Rhuna webhook, or start distributing magic links manually to a pilot group?

**Recommendation:** Pick 10-15 attendees who've already bought tickets, send them their magic links manually, get feedback before the full launch. Pouneh Bligaard is already asking to see it via LinkedIn.

### 2. Sponsor Intelligence Rollout

3 pilot reports generated. Victor hasn't reviewed or pitched them yet. Revenue potential: €40-325k on top of existing €1.3M sponsorship revenue.

**Decision needed:** Should we push Victor to pitch, or generate reports for all 37 sponsors first?

### 3. Data Quality

- **LinkedIn enrichment is dead** — API deprecated, Proxycurl sunset. 0% LinkedIn coverage. Grid B2B and website scraping are the primary enrichment sources (27% Grid coverage).
- **47% of profiles are data-sparse** — no interests, no goals, just a name + company from Rhuna. These get honest "goals not specified" stubs. As attendees interact with the platform (fill in goals, accept/decline matches), data quality improves automatically.

---

## What's Next (Priority Order)

1. **Open to pilot group** — 10-15 attendees, magic links, collect feedback (can do this week without Rhuna webhook)
2. **Sponsor intelligence pitch** — Victor needs to see and pitch the reports
3. **Schedule Rhuna ingestion** — automated hourly sync so new ticket buyers appear automatically
4. **Email templates** — design polish before enabling the full email lifecycle
5. **CEO dashboard alignment** — matchmaker and CEO dash reading from different data sources

---

## Numbers at a Glance

| Metric | Value |
|---|---|
| Attendees in system | 96 |
| AI matches generated | 234 |
| Average match score | 0.713 |
| Sponsor reports ready | 3 (of 37) |
| Ferd's outreach contacts checked | ~4,500 across 7 tabs |
| Days to event | 41 |
| Infrastructure cost | ~€0.39/attendee |

---

## Risk

The biggest risk isn't technical — it's timing. The platform is built but attendees haven't seen it. Every week we wait is a week less for pre-event warm-up, mutual match conversations, and meeting scheduling. The 6-phase attendee journey we designed starts at ticket purchase — we're already behind on that clock.

---

*Prepared by Shaun · April 2026*
