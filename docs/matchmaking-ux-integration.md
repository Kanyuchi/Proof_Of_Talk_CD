# Matchmaking in the Attendee Experience

**For:** Zohair  
**From:** Shaun  
**Date:** 2026-04-19  
**Question:** "How would be the best way to integrate matchmaking in the user experience — when do they see what?"

---

## The core principle

Matchmaking shouldn't be a separate feature attendees go find. **It should BE the experience from the moment they buy a ticket.** The ticket isn't just entry to the Louvre — it's access to an AI that works for them before, during, and after the event.

---

## The timeline

```
BUY TICKET ──→ WARM UP ──→ PREP ──→ AT EVENT ──→ AFTER
  (Day 0)     (weeks)    (48h)    (Jun 2-3)    (D+1-7)
```

---

## Phase 1: Instant — "Your matchmaker is working" (Day 0)

**Trigger:** Rhuna payment confirmed → webhook → Supabase attendee created + magic token generated

**What they see:**

- **Confirmation email** (part of the ticket flow, not a separate email): *"Your AI matchmaker is now analyzing 2,500 decision-makers to find your most valuable meetings at POT 2026. Here's your private briefing link."*
- **Magic link → onboarding page** (3 questions, 60 seconds):
  1. "What's your #1 goal at POT?" (free text)
  2. "Anyone you specifically want to meet?" (free text — feeds `target_companies`)
  3. "Your LinkedIn URL" (optional, improves matching)
- They **don't need to create an account**. No password. The magic link IS their access.

**Why this matters:** You capture intent data while excitement is highest (just bought a €1,200+ ticket). Every field they fill makes their matches dramatically better. And they leave feeling "something is already working for me."

---

## Phase 2: First Matches — "Here's who you should meet" (24-48h after purchase)

**Trigger:** Pipeline runs nightly → ICP inferred → embeddings → matches generated

**What they see:**

- **Email**: *"5 people you should meet at POT 2026"* — top match name, title, company, one-line explanation, magic link CTA
- **Magic link → match dashboard**: full briefing with all matches ranked, explanations, social links, "I'd like to meet" / "Maybe later" buttons
- Each match card shows **WHY**: *"Marcus runs custody infrastructure that could solve your sovereign fund's tokenisation mandate"*

**Why this matters:** This is the moment they realise the ticket was worth it. A generic conference says "network with 2,500 people." POT says "meet THESE 5, here's why, and here's what to talk about."

---

## Phase 3: Warm-Up — "Start conversations before you arrive" (2-6 weeks before)

**What they see:**

- **Weekly digest email**: *"2 new matches this week + 1 mutual accept"*
- **Warm-up threads**: vertical-based group discussions. Their sectors highlighted first.
- **Mutual matches**: when both sides accept, unlock messaging + meeting scheduling
- **Meeting slot picker** for June 2-3

**Why this matters:** Conferences fail when people arrive cold. By the time they walk into the Louvre, they should already have 3-5 scheduled meetings with people they've been exchanging messages with for weeks. The event becomes about **executing deals**, not hunting for them.

---

## Phase 4: Final Briefing — "Your POT 2026 playbook" (48h before)

**What they see:**

- **Email**: *"Your Meeting Brief — POT 2026"*
- **PDF/page**: all confirmed meetings (time, location, person), AI-generated prep notes per meeting (talking points, shared context, deal scenarios), QR code for their badge
- **Concierge**: *"Anything else you need before arriving? Ask your AI concierge."*

**Why this matters:** They arrive prepared, not overwhelmed. A sovereign fund allocator walks in knowing exactly who they're meeting at 10am, what VaultBridge does, and what to ask about custody.

---

## Phase 5: At-Event — "Your meetings are today" (June 2-3)

**What they see:**

- **Morning notification**: *"You have 3 meetings today. First: Marcus Chen @ 10:00 in Salon Apollo."*
- **QR badge** links to their profile
- **Quick feedback** after each meeting: thumbs up/down + one-line note (feeds the ML loop for next year)
- **Real-time suggestions** (stretch goal): *"Amara from Abu Dhabi SWF is in the same session right now"*

---

## Phase 6: Post-Event — "Keep the momentum" (D+1 to D+7)

**What they see:**

- **D+1 email**: *"Your POT 2026 wrap-up: 4 meetings, 2 strong connections. Here's how to continue."*
- LinkedIn connect prompts for mutual matches
- Contact export (CSV/vCard)
- **D+7 nudge**: *"Have you followed up with Marcus? Deals close in the first week."*

---

## What's already built vs what's needed

| Phase | Status | What's missing |
|---|---|---|
| 1. Instant | Partial | Rhuna webhook exists but onboarding page doesn't. Magic links exist but aren't distributed post-purchase. |
| 2. First Matches | Partial | Match pipeline works, email template exists but disabled. Need to enable + connect to post-purchase flow. |
| 3. Warm-Up | Built | Threads, messaging, scheduling, weekly digest — all exist. Just need emails turned on. |
| 4. Final Briefing | Not built | AI Meeting Prep Briefs partially done via concierge. Need a formal briefing page/PDF. |
| 5. At-Event | Partial | QR badges, feedback buttons exist. Real-time suggestions not built. |
| 6. Post-Event | Not built | Contact export, follow-up nudge emails not built. |

---

## The critical unlock

Everything is blocked on Phase 1. Right now attendees buy tickets on Rhuna but can't access anything on our platform. The single highest-impact thing to ship:

> **Rhuna ticket purchase → automatic magic link email → matches visible within 24h**

No registration form. No password. Just: buy ticket → get link → see matches. That's 80% of the value in 20% of the effort.

### What it takes to activate this

1. **Turn on the Rhuna webhook flow** — already built at `/api/v1/integration/ticket-purchased`. When Rhuna sends a purchase event, we create the attendee + generate a magic token automatically.
2. **Re-enable the match intro email** — remove one `return` line in `email.py`. The email template already includes the magic link CTA + QR code.
3. **Add the onboarding questions to the magic link page** — the page exists (`/m/:token`). Adding 3 fields (goals, target_companies, LinkedIn) is a few hours of work.
4. **Schedule the nightly match pipeline** — already runs at 02:00 UTC. New attendees get picked up in the next cycle.

That's it. The infrastructure exists. The pipeline works. The emails are written. We just need to connect the dots and flip the switch.
