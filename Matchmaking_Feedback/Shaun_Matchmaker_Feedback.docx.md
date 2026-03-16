

| PROOF OF TALK 2026 AI MATCHMAKER Product Feedback for Shaun March 2026  •  From Z  •  Sorted by Priority |
| :---: |

# **Report Card**

*Where we stand today. The brain is A+. The body needs a wardrobe upgrade before it walks into the Louvre.*

| Category | Grade | Comment |
| :---- | ----- | :---- |
| **AI Intelligence & Matching Logic** | **A** | Smarter than products that cost €50K+. Match categories, deal readiness, suggested openers — this is the real deal. |
| **Match Explanation Quality** | **A+** | Best in class. "$200M into tokenised real-world assets" beats Grip’s generic tags. |
| **Competitive Differentiation** | **A-** | Beats Grip, Brella & Swapcard on AI intelligence, zero-friction access, and cost. |
| **Feature Completeness** | **B-** | Dashboard, matches, profiles, scheduling, messaging — it’s all there. Problem: half doesn’t work yet. |
| **UX & User Flow** | **C+** | Too many steps, too many tabs. Accept/Reject feels like Tinder. C-suite doesn’t swipe. |
| **Microcopy & Tone of Voice** | **C** | "Accept Meeting" / "Enrich Profile" — reads like a CRM, not a luxury concierge. |
| **Mobile Readiness** | **C** | Dark mode only. Not tested on actual phones. 70% will open match email on mobile first. |
| **Visual Design & Brand Alignment** | **D+** | Looks like a dev side project, not the Louvre. Zero connection to Proof of Talk brand. |
| **Bug-Free Reliability** | **D** | URL validation breaks registration. Messaging empty. Scheduling broken. JS prompt exposes server IP. |
| **Day-of-Event Utility** | **D** | No "My Schedule" view. No way to find next meeting. No event-day features. |

| Overall GPA: B- (2.8/4.0) — The brain is A+. The body needs a wardrobe upgrade before it walks into the Louvre. Fix the bugs, dress it in POT’s brand, and this becomes the smartest person in the room. Which... is kind of the whole point. |
| :---- |

# **✅ What’s Working Well (Keep This)**

* **Match Categories are smart** — Complementary / Deal Ready / Non-Obvious is better than Grip, Brella, or Swapcard. Keep this.

* **Match explanations are specific** — "$200M into tokenised real-world assets," "Abu Dhabi Sovereign Wealth Fund connections." Not generic. This is the core value proposition.

* **Sectors / Synergies / Discuss triptych** — quick-scan view of what they have in common. Competitors don’t do this at this granularity.

* **Suggested Opener with Copy button** — reduces cold outreach barrier. No competitor does this. Keep and refine.

* **Organizer Dashboard** — Total Attendees, Matches Generated, Avg Match Score, Match Type Breakdown, AI Processing Coverage. Strong foundation.

* **Deal Ready Score** — no competitor signals deal readiness. For POT’s investor/allocator audience, this is highly relevant.

| 🛑  MUST FIX — Before Any Real User Touches This These issues destroy trust. A product for high-value users is judged less on features than on whether every click feels intentional and reliable. |
| :---- |

### **1\. Fix URL Validation — Blocks Registration**

Company website field rejects www.xventures.de and shows a German browser error ("Gib eine URL ein"). Attendees will abandon registration. Auto-normalize URLs — if a user enters linkedin.com/in/..., auto-prepend https://. Never require users to manually enter protocol.

**Effort: 30 min  |  Impact: Unblocks registration entirely**

### **2\. Fix or Hide Messaging — Empty Page**

Clicking "Send Message" from a match card leads to an empty Messages page showing "0 conversations" even after a mutual match was accepted. The messaging flow is disconnected from the match acceptance flow. If it doesn’t work, hide it.

**Effort: 2-4 hrs  |  Impact: Removes broken experience**

### **3\. Remove Raw JavaScript Prompt on Decline**

When declining a match, a native browser prompt() dialog appears showing the raw server IP address (54.89.55.202) in mixed German/English. This looks like a malware popup. Replace with a styled inline component, or remove the decline-reason feature entirely. Also remove all popup dependence — replace with inline expansion cards, slide-over drawers, or dedicated detail pages.

**Effort: 1-2 hrs  |  Impact: Removes amateur UX \+ security concern**

### **4\. Fix or Hide Meeting Scheduling**

The time slot picker doesn’t seem to actually create a real appointment or notify the other person. A broken feature is worse than no feature. If it doesn’t work end-to-end (availability, acceptance, confirmation), remove or relabel to "Express Interest" / "Save to Meet in Paris". Only ship scheduling when it’s real.

**Effort: 2-4 hrs to hide, 2-3 days to fix  |  Impact: Removes false promise**

### **5\. Add Success/Failure States Everywhere**

Every CTA must have a clear success state ("Intro request sent," "Meeting request delivered," "LinkedIn opened"). No blank redirects, ever. Add system feedback for every interaction: loading → success → failed → retry.

**Effort: 4-8 hrs  |  Impact: Trust foundation**

### **6\. Ensure Perfect Mobile Experience**

Many attendees will access from email on phone. Requirements: zero popup reliance, sticky CTA buttons, large tap targets (min 44px), fast loading (\<3 seconds), no hidden hover-only states, all actions (copy link, open LinkedIn, request intro) must work on mobile. Match cards with 3-column layout (Sectors/Synergies/Discuss) must stack vertically on mobile. Time slot pills must be large enough to tap. Navigation needs bottom tabs on mobile (My Matches \+ Schedule \+ Profile).

**Effort: 1-2 days  |  Impact: 70% of users will open this on mobile first**

| 🎯  MUST IMPROVE — Before Launch to Attendees These are the upgrades that turn the MVP into something worthy of the Louvre. |
| :---- |

### **7\. Align Visual Design to POT Brand**

The app looks like a generic SaaS product, not the Louvre. Zero visual connection to Proof of Talk. Adopt POT’s color palette, typography, and visual language. Use the actual Proof of Talk logo, not "POT Matchmaker" with a sparkle icon. Design direction: dark, elegant, restrained. Editorial typography. Luxury spacing. Fewer colors. Less "dashboard," more "private briefing dossier." C-suite attendees should open this and immediately recognize it as Proof of Talk.

**Effort: 1-2 days  |  Impact: Brand alignment \+ premium perception**

### **8\. Add Real Profile Photos**

Every match card shows colored circles with initials. For recognizing people in a crowded palace, this is a problem. Priority order: (1) public LinkedIn photo, (2) Rhuna ticket photo if available, (3) company team page headshot, (4) initials fallback, (5) optional user upload. Without photos, cards feel abstract. With photos, they feel human and actionable.

**Effort: 4-8 hrs  |  Impact: Trust \+ event-day recognition**

### **9\. Reduce Registration Friction**

Currently asks for 10+ fields across 3 steps. Too heavy. Since Rhuna handles ticketing, can we prefill and just let the user optimize? Ideal: receive attendee data via API/webhook from Rhuna, prefill everything, let user adjust. The system scrapes the rest. Maximum 2 additional free-text questions.

**Effort: 1-2 days  |  Impact: Higher completion rate**

### **10\. Simplify Action Model — One Primary CTA**

Currently: send message, get in touch, create appointment, connect via external link. Too many overlapping actions. New model: Primary \= "🤝 Request Introduction" (core CTA on every card). Secondary \= "💾 Save for Later" \+ "🔗 Open LinkedIn." Replace "Accept Meeting / Not Now" with softer "Interested" / "Maybe later" — the Tinder-like accept/reject doesn’t fit a professional event.

**Effort: 2-4 hrs  |  Impact: Reduces decision fatigue, cleaner UX**

### **11\. Reframe as a Matchmaking Briefing, Not a Directory**

Don’t lead with "AI matchmaking" or "discover attendees." Lead with: "Your Top Introductions for Proof of Talk Paris" / "The 5 Conversations Most Likely to Matter" / "Private Matchmaking Briefing." Show Top 3 must-meet people first, then "More relevant connections." This creates confidence immediately and feels like intelligence, not browsing.

**Effort: 2-4 hrs  |  Impact: Completely changes first impression**

### **12\. Simplify Navigation**

5 tabs is too many. For attendees, only My Matches and My Schedule matter. "Home" is unnecessary after login. "Attendees" (browsing all people) works against the matchmaking premise AND may violate GDPR by exposing the full participant list — any competitor could copy-paste it. "Dashboard" is for organizers only. Create two separate views: attendee (Matches \+ Schedule) and organizer (Dashboard \+ Attendee Management).

**Effort: 4-8 hrs  |  Impact: Cleaner UX \+ GDPR protection**

### **13\. Upgrade All Product Language**

The copy reads like a CRM, not a Louvre concierge. Key changes: "Accept Meeting" → "I’d like to meet" | "Not Now" → "Maybe later" | "Enrich Profile" → hide it (enrichment should be automatic) | "Match Score: 85%" → "Strong match" | "4 AI-recommended connections" → "We found 4 people you should meet at the Louvre" | "WHY YOU SHOULD MEET" → "Why this meeting matters" | "Register your profile and let AI find your perfect connections" → "Tell us what you need. We’ll tell you who to meet." POT’s brand voice is "we don’t claim, we assume."

**Effort: 2-4 hrs  |  Impact: Premium perception across entire product**

| 💡  NICE TO HAVE — Differentiation for 10/10 These separate a good product from a category-defining one. Tackle after must-fix and must-improve are done. |
| :---- |

### **14\. Working Meeting Scheduling with Email Confirmation**

Full end-to-end: availability, acceptance, confirmation, calendar invite, no-show logic. Competitors have rock-solid calendar sync. Let’s optimize ours.

**Effort: 2-3 days**

### **15\. "My Schedule" View for Event Day**

Simple timeline for June 2 and June 3 showing confirmed meetings, times, and locations. This is the screen people will refresh 20 times during the event.

**Effort: 1-2 days**

### **16\. Email Delivery of Matches**

Personalized email with unique link to authenticated dashboard. Subject line that’s personal: "Sarah, we found the custody partner your fund needs" not "Your matches are ready." Show \#1 match in the email. One-click access, no login needed. Should we add a "you have a new match" notification too?

**Effort: 1 day**

### **17\. Match Refresh as Attendee Pool Grows**

Re-run matching when new people register. Your best match might buy their ticket next week.

**Effort: 4-8 hrs**

### **18\. Behavioral Learning**

Competitors refine matches based on user behavior (who they view, what sessions they attend). Our matches are static. Even basic tracking (post-meeting feedback: "How was this match?" 1-5 stars) would start a learning loop.

**Effort: 4-8 hrs**

### **19\. Saved Shortlist \+ "Why This Match" Transparency**

Let users save matches to a personal shortlist. Add small transparency cues: "Based on your stated goal \+ public profile" / "Selected for partnership potential." Also: lightweight profile edit option ("This is not relevant" / "Show me more investors").

**Effort: 4-8 hrs**

### **20\. Post-Event Continuation**

Competitors allow networking to continue after the event. We have no post-event strategy. Also: capture success stories ("Did any of your POT matches lead to a deal?") — these become testimonials for POT 2027\.

**Effort: 1-2 days**

### **21\. Session/Content Matching (Phase 2\)**

Competitors recommend sessions alongside people. Recommend which panels to attend based on profile and interests. Phase 2 after core matchmaking is solid.

**Effort: Multi-day project**

# **The North Star**

| Don’t try to become a full event networking platform. That’s where Grip, Brella, and Swapcard have years of coverage. Own this category instead: *"The highest-quality introductions engine for senior event attendees."* Fewer matches, better matches. Better explanations, not more features. Better brand, more exclusivity. Less friction, more trust. The product should not feel like a marketplace, dating app, or directory. It should feel like a private intelligence briefing, a curated introductions service, and a high-conviction dealmaking concierge. |
| :---- |

# **The Bottom Line**

**What you got right:** The AI core. The match explanations, categories, deal readiness signals, and suggested openers are genuinely better than enterprise competitors charging tens of thousands. The fact that this exists after a sprint is remarkable.

**What needs work:** Everything around the AI core — the UX shell, the visual design, the broken features, the registration flow, the brand integration. The diamond is there; it needs cutting and polishing.

**The strategic play:** POT doesn’t need to compete with Grip or Brella on feature completeness. Those platforms serve 10,000+ person trade shows. POT serves 2,500 elite attendees. The advantage is deeper AI intelligence per person, more specific match explanations, and zero-friction delivery.

| If you execute the MUST FIX \+ MUST IMPROVE items, this goes from B- to A-. That’s a genuine competitive advantage for POT 2026\. Ship it. — Z |
| :---- |

