# Sponsor Intelligence System — Team Brief

**What:** An AI-powered system that generates personalised intelligence reports for each POT sponsor, telling them exactly who they should meet at the conference and why.

**Why:** 24 sponsors are paying €1.015M total. Zero of that is for matchmaking. If even 10 sponsors buy a €10-15k intelligence add-on, that's €100-150k in new revenue from a system we already have 90% of.

---

## What the sponsor gets

A report (PDF or live dashboard) delivered 2-4 weeks before the event:

```
ZIRCUIT — POT 2026 Intelligence Briefing
=========================================

Your company: EVM-compatible ZK rollup (Blockchain Platforms)
Verified by The Grid ✓

YOUR TOP 20 TARGET ATTENDEES:

1. Mark Creaser — Investor Pass — Astrid Global
   Why: Actively deploying capital into infrastructure. Zircuit's 
   ZK rollup aligns with his thesis on scalable settlement layers.
   → Open with: compliance module roadmap
   → Deal readiness: HIGH

2. Kaushik Sthankiya — VIP — Kraken
   Why: Exchange infrastructure team. Potential integration partner 
   for Zircuit's bridge and settlement layer.
   → Open with: exchange integration case studies
   → Deal readiness: MEDIUM

3. Laurence Filby — VIP Black — The QRL
   Why: Post-quantum cryptography focus. Zircuit's ZK proofs face 
   the same quantum threat — natural research collaboration.
   → Open with: quantum-resistant ZK research
   → Deal readiness: LOW (research stage)

... (20 targets total)

SECTOR BREAKDOWN:
- 8 investors actively deploying into your sector
- 5 potential integration partners (exchanges, wallets)
- 4 complementary infrastructure builders
- 3 regulatory/compliance contacts relevant to ZK rollups
```

---

## How it works (technical)

```
Step 1: Sponsor company name (from Rhuna sponsorship sheet)
         ↓
Step 2: Query The Grid API → get verified sector, products, description
         (9 of 24 sponsors already in Grid, rest use manual description)
         ↓
Step 3: Build composite text from Grid data → generate embedding vector
         ↓
Step 4: pgvector similarity search against ALL 81+ attendee embeddings
         → returns top 30 most relevant attendees
         ↓
Step 5: GPT-4o re-ranks and explains WHY each attendee matters 
         to THIS specific sponsor (not generic — uses Grid products,
         attendee goals, intent tags, deal readiness)
         ↓
Step 6: Output as PDF report or sponsor dashboard page
```

**What already exists (90%):**
- The Grid API integration (fetches company data, hardened with retries)
- All attendee embeddings in pgvector (81 attendees, 1536-dim vectors)
- GPT-4o ranking + explanation engine (already generates match explanations)
- The matching pipeline logic (retrieve → rank → explain)

**What needs to be built (10%):**
- Script/endpoint that runs the pipeline for a company instead of a person
- PDF or HTML report template
- Sponsor data ingestion (from the Google Sheet or manual entry)

---

## Three tiers we can sell

| Tier | What sponsor gets | Price | Engineering effort |
|------|-------------------|-------|--------------------|
| **Intelligence** | Pre-event report: "Your top 20 targets, why they matter, how to open" | €5-10k | Already possible — just a script |
| **Priority** | + Their team members ranked higher in relevant attendees' match lists | €15-25k | ~20 lines of code in matching.py |
| **Exclusive** | + "Featured connection" badge on match cards + post-event ROI report | €50k+ | ~1 day frontend + backend |

---

## What we need from each person

### Victor / Sales
- **Validate pricing** — are €5-10k / €15-25k / €50k+ the right price points for these sponsors?
- **Identify 3-5 pilot sponsors** to generate test reports for — ideally ones Victor has a relationship with and can pitch quickly
- **Share any sponsor briefs** — do sponsors submit what they're looking for? If not, we use Grid data + their company description

### Swerve / Rhuna
- **Sponsor data access** — we need a reliable way to get the sponsor list with: company name, tier, contact person email, any description of what they want from POT
- Currently we pulled from Google Sheet manually — is there an API or export we can automate?

### Karl / Marketing
- **Report design** — the intelligence report needs to look premium (these are €5-50k products). Should it match POT brand? Should it be a PDF, a private dashboard page, or both?
- **Sales page copy** — if we're offering this as an add-on, we need a one-pager or email template Victor can send to sponsors

### Jessica / Chiara (1000 Minds)
- **Speaker data quality** — the more complete our attendee profiles are (goals, interests, company descriptions), the better the sponsor reports will be. Every speaker added to the pool enriches the match quality for sponsors
- **Grid coverage** — currently 23% of attendees have Grid verification (19/81). Can we prioritise getting more companies verified on thegrid.id?

### Engineering / Kanyuchi
- **Build the report generator** — estimated 1-2 days
- **Build Priority boost** — ~2 hours (small scoring multiplier)
- **Build Exclusive tier** — ~1 day (badge component + ROI tracking)

---

## Revenue projection

| Scenario | Sponsors buying | Avg price | Revenue |
|----------|----------------|-----------|---------|
| Conservative | 5 sponsors × Intelligence | €8k | €40k |
| Base case | 10 × Intelligence + 3 × Priority | €12k avg | €145k |
| Optimistic | 15 × Intelligence + 5 × Priority + 2 × Exclusive | €15k avg | €325k |

All on top of the existing €1.015M in sponsorship revenue.

---

## Timeline

| Week | What happens |
|------|-------------|
| **This week** | Build report generator, generate 3 pilot reports |
| **Week 2** | Victor pitches pilot sponsors with real reports |
| **Week 3** | Iterate on report based on feedback, build Priority boost |
| **Week 4+** | Scale to all interested sponsors, build Exclusive tier if demand |

The event is June 2-3. We have ~8 weeks. The Intelligence tier can be ready to sell THIS WEEK.

---

## Key question for the team

> Should we generate 3 pilot reports NOW (for Zircuit, BitGo, and CertiK — all in The Grid) so Victor has something real to show sponsors this week?

This costs nothing except ~30 minutes of compute time and produces tangible sales material.

---

*Prepared by Kanyuchi · April 2026*
