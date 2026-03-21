# What's Next — POT Matchmaker

**Original Goal:** Ship a Level 3 XVentures Labs submission — a working, demo-ready AI matchmaking product that proves intelligent (not keyword-based) matching at Proof of Talk 2026 scale. The bar: does it feel like a product a decision-maker would actually use?

---

## Now

1. **Full end-to-end journey test** — accept a match (both sides), verify mutual match flow, schedule a meeting, download ICS, test in-app messaging between mutual matches
2. **Activate SES email** — verify sender identity in AWS SES console, confirm password reset + match notification emails arrive end-to-end

## Soon

- **Mutual match nav badge** — show pending count on `/matches` nav item so attendees know when someone accepted them without checking manually
- **Wire ML feedback loop** — pass prior decline reasons as negative examples into GPT re-ranking prompt; satisfaction scores are already captured in DB, just not fed back
- **Match card transparency cues (item #19 remainder)** — inline "Why this match" context on each card ("Based on your stated goal + public profile"); lightweight "Show me more like this" / "Not relevant" feedback buttons next to each match card

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
