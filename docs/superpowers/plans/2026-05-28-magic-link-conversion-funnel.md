# Magic-link conversion funnel - 4-phase plan

**Started:** 2026-05-28 (planning session)
**Status:** SPEC'D, NOT YET IMPLEMENTED. Implement in a fresh session.
**Triggered by:** Elliptic walk-through 2026-05-28 12:00 CEST. Sponsor team complained that matches don't convert / Martijn thought decline didn't work / 20 matches felt too few. Cap was raised to 50 in commit `5ea9cce`; but Playwright audit of Ylli's magic link (this session) found that even with 38-44 matches surfaced, the magic-link page is NOT funnelling users into account claim - the primary CTA is collapsed, the nav says "Register" when the user already has an account, and 24 fully-rendered cards with accept buttons give the in-app value without ever asking for the conversion.

**Anchor memory:** `feedback_magic_link_preview_only.md` - magic link MUST stay a preview/conversion funnel, never become a full-feature surface that replaces the logged-in app.

**Shaun's call (2026-05-28):** ship all 4 phases below, in this order, fresh session, with TDD + smoke + review checkpoints between phases.

---

## Phase 1 - Quick wins (copy + layout, no API work)

### Acceptance criteria

- [ ] `MagicMatches.tsx`: the "Set your password" panel is **expanded by default** for magic-link visitors who have NO `users` row (the canonical "unclaimed account" signal). The `+`/`-` toggle stays for users who want to collapse it.
- [ ] `Layout.tsx`: when on a `/m/{token}` route, the bottom-nav "Register" link is **hidden** OR renamed to "Claim account". Magic-link visitors already have an attendee profile; "Register" is misleading. "Sign in" stays.
- [ ] The top-right icon row (Sign in / Register icons in the header) gets the same treatment: drop the Register icon on magic-link routes.
- [ ] The PWA "Install PoT Matchmaker" banner is **demoted** - moved below the Welcome heading, smaller, or gated to "after the user has either claimed an account OR scrolled past 5 match cards". Right now it eats prime real estate above the most important conversion CTA.
- [ ] **Reorder the top sections** so the claim panel ("Set your password") appears BEFORE the "Help us find better matches" data-collection card. The order today is backwards: we ask for Twitter handle before we ask for the account.

### Smoke

- Open Ylli's magic link in Playwright on a 390x844 mobile viewport. Confirm: claim panel expanded, no "Register" in nav, claim panel above the data-collection card, PWA banner demoted.
- Toggle a claimed test attendee (one with a `users` row) and confirm the page still renders normally - the new default-expand logic shouldn't break for someone who's just opening the link as a return visitor.

### Files touched

- `frontend/src/pages/MagicMatches.tsx` - default-expand logic + section reorder
- `frontend/src/components/Layout.tsx` (or wherever the bottom nav lives) - hide Register on `/m/` routes
- `frontend/src/components/PWAInstallPrompt.tsx` (or similar) - demote / gate

### Effort

~1-2 hours including smoke. Pure frontend.

---

## Phase 2 - Reciprocity reveal at top of magic link

### Acceptance criteria

- [ ] New endpoint: `GET /matches/m/{token}/incoming-summary` returns `{count_pending_for_you: int, count_accepted_back: int}`. No auth needed (token is the auth surface). 200 always; 0/0 if none.
  - `count_pending_for_you` = matches where someone OTHER than the token-holder has accepted (status_a or status_b = "accepted") AND the token-holder has not accepted yet.
  - `count_accepted_back` = matches where the token-holder accepted AND the counterpart has also accepted (mutual matches that landed because the OTHER party accepted back).
- [ ] On `MagicMatches.tsx`, a new banner-card appears at the top (between Welcome and the claim panel) when count_pending_for_you > 0:
  - Copy: *"{count} people accepted your interest. Set a password to message them."*
  - CTA: opens the existing claim panel via `setClaimOpen(true)` with `pendingAcceptPersonName` set to a generic "Confirm your account to message your matches".
- [ ] Same banner styling for count_accepted_back > 0 if count_pending_for_you = 0. Copy: *"You have {count} mutual matches waiting. Set a password to start the conversation."*
- [ ] If both counts are 0, the banner does not render (don't manufacture urgency).

### Smoke

- Pick a magic-link with at least one mutual match in DB (Aylin has `Mickey Negus` accept-back per the earlier query); confirm the banner renders.
- Pick a magic-link with no incoming accepts; confirm no banner.

### Files touched

- `backend/app/api/routes/matches.py` - new endpoint
- `backend/app/api/routes/matches.py` - test it
- `frontend/src/api/matches.ts` - client fn
- `frontend/src/pages/MagicMatches.tsx` - banner render + tap-handler

### Effort

~3-4 hours including TDD + smoke.

---

## Phase 3 - Maybe-later microcopy + Concierge gating

### Acceptance criteria

- [ ] When a magic-link user clicks "Maybe later" on a match card, a small inline microcopy appears below it for 5 seconds: *"They'll resurface next session. Want to skip them permanently? Set a password to decline →"* with the underlined link opening the claim panel. After 5s the microcopy fades. Only show this on the FIRST "Maybe later" of the visit (don't nag).
- [ ] AI Concierge floating button on `/m/{token}` routes: for non-claimed users, clicking opens the claim panel (same as the existing "I'd like to meet" hook) with copy *"AI Concierge - claim your account in 10 seconds to chat"*. For claimed users, normal Concierge open.

### Smoke

- Tap "Maybe later" on a magic link - confirm the microcopy renders, fades. Tap again on a second card - confirm it does NOT render (already shown this visit).
- Tap the AI Concierge floating button as a non-claimed user - confirm the claim panel opens with the Concierge copy.

### Files touched

- `frontend/src/pages/MagicMatches.tsx` - microcopy state + 5s timer
- `frontend/src/components/ChatWidget.tsx` (or wherever the floating button lives) - magic-link branch
- `frontend/src/hooks/useFirstActionOfVisit.ts` (new) - state for the "only first time" guard

### Effort

~2-3 hours.

---

## Phase 4 - Match-pool paywall (the BIG conversion lever, BIG UX trade-off)

### Acceptance criteria

- [ ] `MagicMatches.tsx`: on the magic-link route, render the curated tier in full (top 8 with rich explanations + I'd like to meet + Maybe later). Below the curated divider, render a **paywall card** instead of the 30+ deep-tier cards:
  - Headline: *"You have {N} more matches in your pool"* (N = total - 8)
  - Subhead: *"Set a password to unlock your full match list, message them, and book meetings at the Louvre."*
  - CTA button (orange, large): "Unlock my full match list" → opens the existing claim panel
  - Visual treat: small avatars of the next 3-5 matches faded behind the paywall (proof there's more, but masked)
- [ ] Backend `GET /matches/m/{token}` already returns the full list - the truncation is FRONTEND-ONLY on the magic-link surface. The same endpoint serving the logged-in app should NOT truncate.
- [ ] A claimed-account magic-link visit (token-holder has a `users` row) does NOT truncate - they're already converted, show them everything.

### Smoke

- Open Ylli's magic link as the unclaimed user - confirm only 8 curated render, paywall card appears, "Unlock my full match list" opens the claim panel.
- Claim the account in the smoke test (set a password) - confirm the post-claim redirect to `/matches?accepted=1` shows the full 38 matches (this is the in-app surface, not the magic link).

### Files touched

- `frontend/src/pages/MagicMatches.tsx` - truncation logic + paywall component
- `frontend/src/components/MagicLinkPaywall.tsx` (new) - the paywall card

### Trade-off to be aware of

This is the strongest conversion lever and the only phase with strategic implications. It also reduces the magic link's "preview is so good you want full access" effect to a real paywall. Possible sponsor reaction: *"You're gating my matches behind an account?"* - mitigation: the 8 curated are the highest-quality + most-likely-to-act-on, and the upgrade is 10 seconds of password-setting, not a paid upgrade. Worth pre-deciding the response.

### Effort

~3-4 hours.

---

## Total scope

- 4 phases, ~10-13 hours total, all frontend except one tiny backend endpoint
- All gated behind the magic-link route - the logged-in app is unchanged
- No migrations
- No env vars
- All reversible (revert the PR)

## Next session pickup

1. Read this plan + `feedback_magic_link_preview_only.md` memory
2. Read latest `MagicMatches.tsx` (it has the 2026-05-26 conversion-hook pattern + 2026-05-27 register-race fix - don't undo either)
3. Start with Phase 1 (copy/layout) - lowest risk, fastest feedback
4. Smoke each phase via Playwright before moving to the next
5. PR per phase OR one PR with 4 commits - Shaun's call when starting

## Out of scope (separate work)

- Adding a Decline button to magic-link cards - explicitly rejected (`feedback_magic_link_preview_only.md`)
- Phase 5/6 emails (`send_post_event_wrapup_email`, `send_followup_nudge_email`)
- The `[sponsor-curated-count-boost]` follow-up from today's session_log
- The `[reclassify-paying-sponsors-to-SPONSOR-ticket-type]` audit
