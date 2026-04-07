# Matchmaking as a Revenue Driver
## Strategy Brief for Marketing Team

**Core thesis:** The matchmaking engine shouldn't just serve attendees after they buy — it should be the reason they buy. And it should be a premium sponsors can pay for.

---

## The Problem Today

Right now the matchmaking engine activates **after** ticket purchase. The attendee buys a ticket on Rhuna, gets synced into the system, gets enriched, gets matched. But nobody sees the value of matching until they've already paid.

**What we're leaving on the table:**
- No pre-purchase preview of who you could meet → no urgency to register
- No differentiation between ticket tiers beyond access level → no upsell lever
- Sponsors get the same matching as everyone else → no premium to sell
- No post-event proof of ROI for sponsors → harder to renew

---

## Strategy: Three Revenue Levers

### Lever 1: Drive Ticket Sales (Pre-Purchase Matchmaking Preview)

**Concept:** Show potential attendees a taste of who they could meet *before* they buy.

| Tactic | How It Works | Effort |
|--------|-------------|--------|
| **"See Who's Attending" public page** | Public speaker directory from 1000 Minds (Jessica's list) + anonymised attendee stats by vertical. "47 investors, 33 infrastructure builders, 12 regulators already registered." No names — just enough to trigger FOMO. | Medium |
| **"Preview Your Matches" landing page** | Visitor enters their name, title, company, and "what they're looking for" → AI generates 3 sample match previews (blurred names, real explanations). CTA: "Buy a ticket to unlock your full briefing." | Medium |
| **Post-registration email sequence** | After ticket purchase: (1) Welcome + "complete your profile" with magic link, (2) "Your first 3 matches are ready" with QR code, (3) Weekly "new attendees in your sector" digest, (4) 48h before event: "Your final briefing is ready." | Small (email provider needed) |
| **VIP upsell in matching** | General Pass holders see top 5 matches. VIP Pass holders see top 10 + get priority placement in others' recommendations. "Upgrade to VIP to unlock 5 more high-value introductions." | Small |
| **Referral via QR code** | Attendees share their QR code → referred person sees a "You were invited by [Name] — register to see your own matches" landing page with discounted/comp ticket link. | Medium |

**Revenue impact:**
- Increases conversion rate (currently 54.8%) by giving prospects a concrete reason to buy
- Creates natural upsell path from General (€839) to VIP (€1,200+)
- Referral loop generates organic registrations at lower acquisition cost

---

### Lever 2: Increase Sponsorship Value (Sponsor Intelligence Package)

**Concept:** Offer sponsors a premium "Intelligence Package" that uses the matching engine and Grid data to deliver measurable ROI.

| Feature | What Sponsors Get | How It Works |
|---------|------------------|-------------|
| **Sponsor Match Report** | Pre-event briefing: "Here are the 20 attendees most likely to need your product/service" | AI generates sponsor-specific matches based on company profile + attendee intent tags |
| **Priority Matching** | Sponsor team members appear higher in relevant attendees' recommendation lists | Boost score for sponsor employees in the ranking algorithm |
| **Sponsored Match Card** | "Recommended by [Sponsor]" badge on match cards | Visual branding on match cards that are relevant to sponsor's sector |
| **Lead Capture Dashboard** | Real-time view: which attendees are in their sector, who accepted their matches, meeting pipeline | Sponsor-specific dashboard filtered to their vertical + connections |
| **Post-Event ROI Report** | "Your team had 47 AI-recommended introductions, 23 accepted, 8 meetings scheduled, 3 deals in pipeline" | Automated PDF from match data |
| **Sponsored Thread** | Branded warm-up thread in the pre-event discussion area | Pin sponsor's thread to top of threads list with sponsor branding |

**Pricing model:**
- **Bronze:** Logo on match cards in their sector — included in Sponsor Pass
- **Silver:** + Priority matching + sponsored thread — €5,000 add-on
- **Gold:** + Sponsor Match Report + lead capture dashboard + post-event ROI report — €15,000 add-on

**Revenue impact:**
- Currently 1 sponsor ticket sold. With a tiered intelligence package, sponsor value increases from ticket price alone (€839–€2,000) to €5,000–€15,000 per sponsor
- At 20 sponsors with avg Silver package: €100,000 additional revenue

---

### Lever 3: Post-Event Value Lock (Retention & Renewal)

**Concept:** The matchmaking relationship doesn't end when the event ends. Keep the network active year-round to drive next-year ticket sales.

| Feature | Value |
|---------|-------|
| **Year-round directory** | Attendees can access their match briefing and connections after the event |
| **Deal tracker** | Track which introductions led to deals — proof of event ROI |
| **D+7 follow-up email** | "You met 5 people at POT — here's your connection summary + LinkedIn links" |
| **Early-bird for returners** | "Your POT 2026 matches generated 3 deals. Lock in POT 2027 at 30% off." |
| **Sponsor renewal pitch** | Automated sponsor ROI report → "Your Gold package generated €2.4M in pipeline. Renew for 2027?" |

---

## What We Need From Marketing

### Immediate (this week)
1. **Landing page copy** for "See Who's Attending" — we build the page, marketing writes the messaging
2. **Email sequence copy** for post-purchase flow — 4 emails (welcome, first matches, weekly digest, final briefing)
3. **Sponsor package pricing** — validate Bronze/Silver/Gold tiers and pricing with sales team

### Soon (next 2 weeks)
4. **DNS access for `proofoftalk.io`** — we need to add email DNS records to enable batch email delivery (currently blocked)
5. **Sponsor prospects list** — which companies are being pitched for sponsorship? We can pre-build their match reports
6. **Social media assets** — "I'm attending" graphic template that attendees get via email/QR

### Integration Points
7. **Rhuna checkout flow** — can we add the 2 matchmaking questions to the Rhuna ticket purchase? ("What's the one thing you need from this event?" + "Who do you want to meet?")
8. **Karl + Chiara** — post-purchase email sequence needs to be coordinated with existing marketing automation

---

## What's Already Built

| Capability | Status | Commercial Use |
|-----------|--------|---------------|
| AI matching (3-stage pipeline) | Live — 317 matches, 73 attendees | Core product |
| Magic link (no-login access) | Live — QR code in email | Frictionless attendee onboarding |
| Speaker directory (1000 Minds) | Synced — 8 speakers | "See Who's Speaking" page |
| Grid B2B verified data | 19/73 companies verified | Sponsor credibility + company intelligence |
| Investor Heatmap | Live on dashboard | Sponsor pitch: "Here's your audience" |
| Revenue tracking | Live — €42.5k, 68 tickets | Internal KPI |
| Warm-up threads (11 sectors) | Live | Pre-event engagement metric for sponsors |
| "Who do you want to meet?" | Live — field on profile | Explicit intent data for matching + sponsors |
| QR business card | Live — on profile page | Event networking + referral vehicle |
| Match card feedback | Live — thumbs up/down | ML loop for match quality |

---

## Recommended Build Sequence

| Priority | Feature | Revenue Impact | Effort |
|----------|---------|---------------|--------|
| 1 | **Post-purchase email sequence** (4 emails with magic link + QR) | Retention + profile completion + match quality | Blocked on email provider |
| 2 | **"See Who's Attending" public page** (anonymised stats by vertical + speakers) | Ticket conversion | 2-3 days |
| 3 | **VIP upsell in matching** (top 5 vs top 10 matches by tier) | Upsell revenue | 1 day |
| 4 | **Sponsor Match Report** (pre-event briefing PDF for sponsors) | Sponsorship value | 3-4 days |
| 5 | **Sponsor dashboard** (filtered view of attendees + match pipeline) | Sponsorship value | 1 week |
| 6 | **"Preview Your Matches" landing page** (sample matches without buying) | Ticket conversion | 3-4 days |

---

*Prepared by Kanyuchi — April 7, 2026*
