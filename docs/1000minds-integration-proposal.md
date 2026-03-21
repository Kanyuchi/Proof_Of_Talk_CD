# 1000 Minds × POT Matchmaker Integration Proposal

**For discussion with Jes | March 17, 2026**

---

## What We Have: Two Complementary Systems

### 1000 Minds That Matter (your build)
- **Purpose**: Curated directory of top 1,000 decision-makers in digital assets
- **Data model**: Name, company, title, seniority tier, region, verticals, bio, contribution to digital assets, Grid company data
- **Current state**: 1 profile (Larry Fink POC), nomination flow live
- **UX**: Public showcase — "who's in the room"

### POT Matchmaker (my build)
- **Purpose**: AI-powered matchmaking engine for POT 2026 attendees
- **Tech**: LinkedIn enrichment + semantic embeddings + GPT-4o re-ranking
- **Output**: Private Briefing Dossiers with personalized match recommendations, conversation starters, AI Concierge
- **UX**: Private intelligence layer — "who should YOU talk to"

---

## The Opportunity

**Together they create a funnel:**
Discover (1000 Minds directory) → Register (matchmaker) → Get matched → Meet at the Louvre

**Key insight:** The directory is prestige/curation, the matchmaker is activation/personalization.

---

## Proposed Integration Points

### 1. **Shared Identity Layer**
- Use **LinkedIn URL** as the common unique identifier across both systems
- When someone is nominated/listed in 1000 Minds → their structured data (verticals, seniority, contribution) flows into the matchmaker's attendee database
- When someone registers on matchmaker → check if they're in the directory; if not, prompt to get nominated

### 2. **Directory Data as Matchmaking Signal**
- Your structured metadata (verticals, seniority tier, contribution narrative) significantly improves match quality
- Matchmaker currently uses LinkedIn + company websites + funding data — adding your curated fields boosts the AI's understanding of the most important attendees

### 3. **Cross-Linked UX**
- **1000 Minds → Matchmaker**: Each directory profile gets a CTA: "Attending POT 2026? Register to get matched with [Name]"
- **Matchmaker → 1000 Minds**: Match results show a badge ("1000 Minds That Matter") + link to full directory profile when applicable

### 4. **Nomination Pipeline**
- Your nomination form captures: name, company, role, seniority, vertical, LinkedIn, reason
- Once approved → creates profile in 1000 Minds AND flags them as VIP in matchmaker (so other attendees get matched to them with higher priority)

### 5. **AI Concierge Integration**
- Matchmaker's AI Concierge can query: "Who are the top minds in Tokenisation of Finance?" → pulls from your curated directory data, not just general attendee pool

---

## Technical Approach (High-Level)

1. **Shared API or database** — both front-ends read/write to common attendee data
2. **LinkedIn URL** as unique identifier — dedupe and link profiles
3. **Bi-directional CTAs** — users flow naturally between discovery and matchmaking
4. **Vertical tags + seniority tiers** → feed into matchmaker's embedding pipeline for better matches

---

## Discussion Points

1. **Data sync approach** — Should I pull from your Netlify app via API, or do we share a database? What's your current backend (Airtable, Firebase, custom)?
2. **Nomination approval flow** — Who approves nominations? Should approved nominees auto-populate the matchmaker as VIPs?
3. **Public vs. private data** — What from 1000 Minds should be public (directory) vs. enrichment-only (matchmaker internal)?
4. **Timeline** — When do you need this integrated? POT 2026 is June 2-3.

---

**Next Steps:**
Let's align on data sync strategy + approval workflow, then I'll build the integration on the matchmaker side.

— Kanyuchi
