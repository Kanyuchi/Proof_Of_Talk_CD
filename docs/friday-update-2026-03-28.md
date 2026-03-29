Subject: POT Matchmaker — Weekly Update (March 28)

Hey everyone,

Sending you my weekly overview below:

**Key results:**
- All 5 brainstorm Quick Wins shipped (Intent Matching, QR Code, Directory, Investor Heatmap, Warm-Up Threads)
- Magic link access live — attendees see matches with 1 click, no login
- "Who do you want to meet?" field implemented — Z's product direction wired into matching
- Architecture doc + cost analysis delivered (€0.39/attendee at 2,500 scale)

**Progress on last week's priorities:**
- Magic link (no-login access) — **done** (token per attendee, `/m/:token` route, email CTA)
- Architecture/scale documentation — **done** (`docs/architecture-scale.md`)
- Cost analysis — **done** (`docs/cost-analysis.md`, €0.39/attendee, under €0.50 target)
- Scale test to 50 profiles — **pending** (awaiting accurate data from Chiara)
- SES production access — **blocked** (AWS denied case #177412752700989; Victor approved new company AWS account — to be set up)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## What shipped this week

### Magic Link & Email
- **Magic link access**: every attendee gets a unique `/m/:token` URL — 1-click read-only match dashboard, no login required; tokens auto-generated on registration
- **QR code in email**: match intro emails now include a scannable QR code (CID attachment) linking to the magic link — "Or scan to open on your phone"
- **Match intro email copy**: updated from "The AI has matched you" to "Our Matchmaker has matched you"
- **SES verification emails sent** to mona@proofoftalk.io, nupur@proofoftalk.io, hamid@xventures.de, victor@xventures.de, z@xventures.de

### Brainstorm Quick Wins (all 5 shipped)
- **Investor Heatmap**: new dashboard section showing capital activity by sector — who's deploying capital, co-investing, deal-making; deal readiness distribution (high/medium/low)
- **QR Business Card Exchange**: scannable QR on Profile page linking to your magic link; copy link + save as PNG buttons
- **Pre-Event Warm-Up Threads**: 11 sector-based discussion threads (tokenisation, DeFi, infrastructure, AI/DePIN, etc.); your sectors highlighted and sorted first; live polling

### Z's Product Direction (implemented)
- **"Who do you want to meet?"**: new `target_companies` free-text field on Profile page + magic link enrichment card; attendees name companies/people they want to meet
- **Magic link profile enrichment**: attendees can update Twitter + target companies via magic link without logging in
- **Matching integration**: `target_companies` fed into embeddings + GPT-4o ranking prompt with highest priority — explicit user intent overrides AI inference (Z's weight hierarchy)

### UX Polish
- **Auth-aware home page**: logged-in users see "View your matches" / "Edit your profile" instead of sign-in CTAs
- **Feature card copy rewrite**: removed technical jargon ("semantic embeddings", "GPT-4o") — now attendee-facing
- **Social links on match cards**: LinkedIn, Twitter, website icons on every match card
- **Twitter URL fix**: handles full URLs (`https://x.com/handle`) not just `@handle`
- **Mutual match nav badge**: orange count badge on "My Matches" when someone accepted you
- **ML feedback loop**: GPT-4o now receives prior decline reasons as negative examples
- **Match card feedback**: "More like this" / "Not relevant" thumb buttons for lightweight quality signals

### Documentation
- **Architecture & scale doc**: 3-stage pipeline scaling from 38 → 2,500 (pgvector IVFFlat, infrastructure path, runtime estimates)
- **Cost analysis**: €0.39/attendee optimised (2×/week refresh), under the €0.50 KR 3.3 target
- **Customer journey diagram**: complete Mermaid flowchart — ticket purchase → enrichment → matching → email → magic link → accept → mutual match → meeting → feedback

## By the numbers

| Metric | Last Week | This Week | Change |
|--------|-----------|-----------|--------|
| Attendees | 38 | 41 | +3 |
| Matches | 129 | 140 | +11 |
| Enrichment coverage | 100% | 100% | — |
| Avg match score | 0.69 | 0.70 | +0.01 |
| Matches above 0.75 | — | 36 | tracked |
| Brainstorm Quick Wins | 2/5 | 5/5 | +3 |
| OKR Definition of Done | 4/6 | 5/6 | +1 |

**OKR Scorecard (Week 2):**

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Registration → auto-enrichment → structured profile | Done |
| 2 | 50+ profiles, ≥3 matches each with explanations | 41 profiles (awaiting Chiara data), ≥3 per person done |
| 3 | Unique link, mobile-responsive, no login required | Done (magic link) |
| 4 | Match email with dashboard link | Done (SES sandbox — email provider switch pending) |
| 5 | Architecture doc for 2,500 scale | Done |
| 6 | Cost per attendee < €0.50 | Done (€0.39) |

## Feedback needed

1. **Email provider**: Victor approved a new company AWS account — when is it ready so I can set up SES?
2. **Chiara**: status on attendee data for the 50-profile scale test?
3. **Brainstorm next tier**: all Quick Wins shipped — which Core Features to prioritise next? (AI Meeting Prep Briefs, Session Matchmaking, Matchmaking Lunch Algorithm, Sponsor Analytics)
4. **Z's vision**: AI-inferred customer matching + company similarity fallback — should I start building this, or focus on email delivery first?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Focus for next week:**
- Set up SES on new company AWS account + verify `proofoftalk.io` domain
- Scale test to 50 profiles (once Chiara provides data)
- Full end-to-end journey test with team (magic link → accept → mutual match → chat → schedule)
- Begin AI-inferred customer matching (Z's vision) or next Core Feature from brainstorm

**Wins Worth Celebrating:**
- All 5 brainstorm Quick Wins shipped in one week
- Magic link access live — true zero-friction attendee experience
- Z's "who do you want to meet?" vision built and wired into matching
- Architecture + cost docs delivered — system scales to 2,500 at €0.39/person
- QR code renders in email — scan to see your matches from your phone
- ML feedback loop closed — the engine learns from declines
- Complete customer journey mapped (Mermaid diagram)

— Kanyuchi
