# POT Matchmaker: Current Taxonomy & Integration Strategy

**Prepared for:** Jes (1000 Minds builder)
**Date:** March 17, 2026
**Purpose:** Ensure tags/taxonomy carry over seamlessly between systems

---

## 1. Current POT Matchmaker Taxonomy

### A. Seniority/Role Classification
**Field:** `ticket_type` (enum)
- **VIP** — Institutional allocators, C-suite decision-makers
- **Speaker** — Thought leaders, company executives
- **Sponsor** — Companies showcasing at POT
- **Delegate** — General attendees

**Field:** `title` (free text)
- Examples from live data: "Director of Digital Assets", "CEO & Co-Founder", "General Partner", "CTO", "Head of Digital Assets Innovation"
- ⚠️ **No standardized seniority extraction** — parsed from free text

---

### B. Geographic Scope
**Field:** `preferred_geographies` (array, free text)

**Currently in use:**
- Europe
- Middle East
- North America
- Asia
- Global

**No controlled vocabulary** — users can enter any region

---

### C. Interest Areas / Sectors / Verticals
**Field:** `interests` (array, free text)

**Currently in use (from seed + live data):**
- tokenised real-world assets
- blockchain infrastructure
- regulated custody
- institutional DeFi
- institutional custody
- tokenised securities
- settlement infrastructure
- banking partnerships
- TradFi-DeFi convergence
- Series A-B investing
- Layer-2 scaling
- enterprise blockchain
- compliance modules
- KYC/AML
- cross-chain settlement
- CBDC
- regulatory frameworks
- MiCA
- tokenised securities regulation
- compliance-first technology

**Pattern:** Granular, technical, no controlled vocabulary
**Total unique values across 23 attendees:** ~60+ different interest terms

---

### D. Deal Stage / Intent
**Field:** `deal_stage` (string, nullable)
- Examples: "Series B", "raising Series A", "pre-seed"
- Free text, inconsistent format

**Field:** `seeking` (array)
- Intended for: "investors", "co-investors", "strategic partners", "customers", "pilots"
- Currently unused (empty arrays in all profiles)

---

## 2. Jes's 1000 Minds Taxonomy

### A. Seniority Tiers (standardized)
- C-Level
- Founder
- GP (General Partner)
- CIO (Chief Investment Officer)
- VP
- Director
- Head of
- Partner

### B. Regions (standardized)
- All Regions (default)
- North America
- Europe
- Asia
- Middle East
- Global

### C. Primary Verticals (standardized)
- Tokenisation of Finance
- Bitcoin
- Decentralised AI
- Investing in Digital Assets
- Privacy
- Prediction Markets

---

## 3. Gap Analysis

| **Dimension** | **POT Matchmaker** | **1000 Minds** | **Alignment Status** |
|---------------|-------------------|----------------|----------------------|
| **Seniority** | `ticket_type` (4 tiers) + free-text `title` | Standardized 8-tier seniority | ⚠️ **PARTIAL** — need to extract/map seniority from titles |
| **Geography** | `preferred_geographies` (free text, multiple) | Standardized 5 regions + Global | ✅ **COMPATIBLE** — values align, just need to standardize |
| **Verticals** | `interests` (~60 granular terms) | 6 high-level verticals | ⚠️ **MAPPING NEEDED** — granular → high-level |

---

## 4. Proposed Harmonization Strategy

### Strategy: **Dual-Layer Taxonomy**

Keep both granular (matchmaker) and high-level (1000 Minds) taxonomies, with bidirectional mapping.

#### Why?
- **Granular interests** (`interests` field) → Better semantic embeddings, richer matching
- **Standardized verticals** (`verticals` field) → Clean filtering, directory display, cross-system sync

---

### A. Seniority Mapping

#### Add to Matchmaker Schema:
```python
seniority_tier: str | None  # Maps to 1000 Minds taxonomy
```

#### Mapping Logic:
```
title contains "CEO", "Chief Executive" → C-Level
title contains "Founder", "Co-Founder" → Founder
title contains "General Partner", "GP" → GP
title contains "CIO", "Chief Investment Officer" → CIO
title contains "VP", "Vice President" → VP
title contains "Director" → Director
title contains "Head of" → Head of
title contains "Partner" → Partner
```

**Implementation:** AI classifier extracts `seniority_tier` from `title` field during enrichment

---

### B. Region Mapping

#### Update Matchmaker Schema:
```python
region: str | None  # Single primary region (1000 Minds standardized)
preferred_geographies: list[str]  # Keep for user preference (can be multiple)
```

#### Mapping:
```
User enters: ["Europe", "Middle East"]
→ Primary region: "Europe" (first in list)
→ preferred_geographies: ["Europe", "Middle East"] (preserved)
```

**Standard values:**
- North America
- Europe
- Asia
- Middle East
- Global

---

### C. Verticals Mapping (Most Important)

#### Add to Matchmaker Schema:
```python
verticals: list[str]  # Standardized 1000 Minds verticals
interests: list[str]  # Keep granular free-text interests
```

#### Mapping Table: Granular → High-Level

| **POT Matchmaker Interests (Granular)** | **1000 Minds Vertical (High-Level)** |
|----------------------------------------|--------------------------------------|
| tokenised real-world assets, tokenised securities, regulated custody, settlement infrastructure, banking partnerships | **Tokenisation of Finance** |
| Bitcoin, Bitcoin ETFs, Bitcoin infrastructure | **Bitcoin** |
| AI agents, decentralised AI, machine learning infrastructure | **Decentralised AI** |
| Series A-B investing, venture capital, co-investment, institutional traction, TradFi-DeFi convergence | **Investing in Digital Assets** |
| privacy protocols, zero-knowledge proofs, confidential computing | **Privacy** |
| prediction markets, forecasting, Polymarket | **Prediction Markets** |
| DeFi, institutional DeFi, Layer-2 scaling, cross-chain settlement, blockchain infrastructure | **Tokenisation of Finance** (if finance-related) or **Investing in Digital Assets** |
| CBDC, regulatory frameworks, MiCA, compliance modules, KYC/AML | **Tokenisation of Finance** (regulatory infrastructure) |

**Implementation:**
- AI classifier reads `interests` array → assigns one or more `verticals`
- Example: `["tokenised securities", "banking partnerships"]` → `verticals: ["Tokenisation of Finance"]`
- Example: `["Bitcoin infrastructure", "privacy protocols"]` → `verticals: ["Bitcoin", "Privacy"]`

---

## 5. Data Flow: Registration → Directory

### Scenario 1: User Registers on Matchmaker
1. User fills free-text `interests`: `["tokenised real-world assets", "regulated custody"]`
2. User selects `preferred_geographies`: `["Europe", "Middle East"]`
3. User enters `title`: `"Director of Digital Assets"`

**Matchmaker auto-classifies:**
```python
{
  "interests": ["tokenised real-world assets", "regulated custody"],
  "preferred_geographies": ["Europe", "Middle East"],
  "title": "Director of Digital Assets",

  # Auto-classified (AI)
  "seniority_tier": "Director",
  "region": "Europe",
  "verticals": ["Tokenisation of Finance"]
}
```

4. If user is nominated to 1000 Minds → these standardized fields sync to your directory

---

### Scenario 2: User Gets Nominated on 1000 Minds
1. Nomination form captures:
   - `seniority_tier`: "Director"
   - `region`: "Europe"
   - `verticals`: ["Tokenisation of Finance"]

2. On approval → creates/updates matchmaker record:
```python
{
  "seniority_tier": "Director",  # From 1000 Minds
  "region": "Europe",             # From 1000 Minds
  "verticals": ["Tokenisation of Finance"],  # From 1000 Minds
  "is_1000_minds": True,

  # User can still add granular interests when they register
  "interests": [],  # Empty until user registers
  "preferred_geographies": ["Europe"]  # Derived from region
}
```

---

## 6. Implementation Plan

### Phase 1: Add Standardized Fields to Matchmaker
```python
# backend/app/models/attendee.py
class Attendee(Base):
    # ... existing fields ...

    # 1000 Minds standardized taxonomy
    seniority_tier: str | None      # One of: C-Level, Founder, GP, CIO, VP, Director, Head of, Partner
    region: str | None               # One of: North America, Europe, Asia, Middle East, Global
    verticals: list[str]             # Array from: Tokenisation of Finance, Bitcoin, Decentralised AI,
                                     #             Investing in Digital Assets, Privacy, Prediction Markets

    # 1000 Minds directory flag
    is_1000_minds: bool = False
```

### Phase 2: Build AI Classifier
Script: `backend/scripts/classify_taxonomy.py`
- Read existing `interests` → assign `verticals`
- Parse `title` → extract `seniority_tier`
- Read `preferred_geographies` → set primary `region`

### Phase 3: Update Registration Forms
- Frontend dropdowns for `verticals` (multi-select from 6 options)
- Frontend dropdown for `region` (single select from 5 options)
- Keep free-text `interests` for granularity
- Auto-classify `seniority_tier` from `title`, allow manual override

### Phase 4: API Integration with 1000 Minds
- Endpoint: `POST /api/sync/1000minds` — accepts your directory data
- Maps your fields → our standardized fields
- Creates/updates attendee with `is_1000_minds=True`

---

## 7. Questions for Jes

1. **Vertical mapping:** Does the mapping table above (Section 5C) accurately capture how you'd group interests into your 6 verticals?

2. **Multiple verticals:** Can a person have multiple verticals? (e.g., someone working on Bitcoin privacy = both "Bitcoin" + "Privacy"?)

3. **Data sync direction:**
   - Should matchmaker **pull** from your API (we query your directory hourly)?
   - Or should you **push** to our API (you call our endpoint when someone is approved)?

4. **Seniority edge cases:**
   - What if someone is both "Founder" and "CEO"? Primary = "Founder"?
   - What about "Managing Director" — map to "Director" or "C-Level"?

5. **LinkedIn URL as unique ID:** Confirm this works for deduplication. What if someone doesn't have LinkedIn?

---

## 8. Recommended Next Step

**Let's align on the vertical mapping table first** (Section 5C), then I'll:
1. Build the AI classifier to populate `verticals`, `seniority_tier`, `region`
2. Add database migration for new fields
3. Create sync API endpoint for your directory data

---

**Prepared by:** Kanyuchi
**Contact:** [Your preferred contact method]
