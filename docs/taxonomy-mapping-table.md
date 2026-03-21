# Quick Reference: Taxonomy Mapping

| **1000 Minds Field** | **POT Matchmaker (Current)** | **Proposed Matchmaker Field** | **Status** |
|----------------------|------------------------------|-------------------------------|------------|
| **Seniority Tier** (C-Level, Founder, GP, CIO, VP, Director, Head of, Partner) | `title` (free text: "CEO", "Director of...") | `seniority_tier` (enum: standardized) | ⚠️ **ADD NEW FIELD** |
| **Region** (North America, Europe, Asia, Middle East, Global) | `preferred_geographies` (array, free text) | `region` (single primary region, enum) | ⚠️ **ADD NEW FIELD** |
| **Verticals** (Tokenisation of Finance, Bitcoin, Decentralised AI, Investing, Privacy, Prediction Markets) | `interests` (array, free text: "DeFi", "tokenised RWA") | `verticals` (array, standardized enum) | ⚠️ **ADD NEW FIELD** |
| **LinkedIn URL** | `linkedin_url` (string, nullable) | `linkedin_url` (string, nullable) | ✅ **EXISTS** — use as unique ID |
| **Contribution to Digital Assets** | — | `contribution_to_digital_assets` (text) | ⚠️ **ADD NEW FIELD** |
| **Directory Bio** | `ai_summary` (AI-generated) | `directory_bio` (curated human bio) | ⚠️ **ADD NEW FIELD** |
| **Is 1000 Minds Member?** | — | `is_1000_minds` (boolean) | ⚠️ **ADD NEW FIELD** |

---

## Data Flow Example

### Scenario: Larry Fink (1000 Minds POC) registers on matchmaker

**1000 Minds Directory Data:**
```json
{
  "name": "Larry Fink",
  "company": "BlackRock",
  "title": "Chairman and CEO",
  "seniority_tier": "C-Level",
  "region": "North America",
  "verticals": ["Tokenisation of Finance", "Investing in Digital Assets"],
  "contribution_to_digital_assets": "Led BlackRock's $10T AUM into Bitcoin ETFs...",
  "directory_bio": "Larry Fink is the Chairman and CEO of BlackRock...",
  "linkedin_url": "https://www.linkedin.com/in/larryfink"
}
```

**POT Matchmaker Attendee Record (after sync):**
```python
{
  "name": "Larry Fink",
  "company": "BlackRock",
  "title": "Chairman and CEO",
  "linkedin_url": "https://www.linkedin.com/in/larryfink",

  # Standardized 1000 Minds fields
  "seniority_tier": "C-Level",
  "region": "North America",
  "verticals": ["Tokenisation of Finance", "Investing in Digital Assets"],
  "contribution_to_digital_assets": "Led BlackRock's $10T AUM into Bitcoin ETFs...",
  "directory_bio": "Larry Fink is the Chairman and CEO of BlackRock...",
  "is_1000_minds": True,

  # User-provided fields (filled if Larry registers via matchmaker)
  "interests": ["institutional Bitcoin adoption", "ETF strategy"],
  "preferred_geographies": ["North America", "Europe"],
  "goals": "Expand BlackRock's tokenised asset product suite...",

  # AI-enriched fields
  "ai_summary": "AI-generated summary combining directory bio + enriched data",
  "embedding": [0.123, 0.456, ...],  # 1536-dim vector
  "deal_readiness_score": 0.95
}
```

**Why both standardized + free-text fields?**
- **Standardized** (`verticals`, `region`, `seniority_tier`) → filtering, directory display, structured matching
- **Free-text** (`interests`, `goals`) → semantic embeddings, conversational AI Concierge, nuanced matching

---

## Embedding Strategy

The composite text for embeddings will combine both:

```
Name: Larry Fink
Title: Chairman and CEO
Company: BlackRock
Seniority: C-Level
Region: North America
Verticals: Tokenisation of Finance, Investing in Digital Assets
Contribution: Led BlackRock's $10T AUM into Bitcoin ETFs...
Interests: institutional Bitcoin adoption, ETF strategy
Goals: Expand BlackRock's tokenised asset product suite...
[+ enriched data from LinkedIn, company website, etc.]
```

**Result:** Best of both worlds — structured filtering + semantic richness
