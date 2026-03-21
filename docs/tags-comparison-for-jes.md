# Tag Comparison: 1000 Minds ↔ POT Matchmaker

**Quick reference for Jes** — Please review and confirm/adjust the mappings below

---

## 1. SENIORITY

| **Your Tags (1000 Minds)** | **My Current Data (Matchmaker)** | **Mapping Strategy** |
|----------------------------|----------------------------------|----------------------|
| C-Level | `title`: "CEO", "Chairman", "Chief..." | ✅ Extract from title |
| Founder | `title`: "Founder", "Co-Founder" | ✅ Extract from title |
| GP | `title`: "General Partner", "GP" | ✅ Extract from title |
| CIO | `title`: "Chief Investment Officer", "CIO" | ✅ Extract from title |
| VP | `title`: "Vice President", "VP" | ✅ Extract from title |
| Director | `title`: "Director of..." | ✅ Extract from title |
| Head of | `title`: "Head of..." | ✅ Extract from title |
| Partner | `title`: "Partner" | ✅ Extract from title |

**Question for you:** What about "Managing Director"? Map to **Director** or **C-Level**?

---

## 2. REGIONS

| **Your Tags (1000 Minds)** | **My Current Data (Matchmaker)** | **Mapping Strategy** |
|----------------------------|----------------------------------|----------------------|
| North America | `preferred_geographies`: "North America" | ✅ Direct match |
| Europe | `preferred_geographies`: "Europe" | ✅ Direct match |
| Asia | `preferred_geographies`: "Asia" | ✅ Direct match |
| Middle East | `preferred_geographies`: "Middle East" | ✅ Direct match |
| Global | `preferred_geographies`: "Global" | ✅ Direct match |
| All Regions (default) | — | Will use this as default if none selected |

**Perfect alignment!** No changes needed.

---

## 3. VERTICALS (Most Important — Please Review!)

### Your 6 High-Level Verticals:
1. Tokenisation of Finance
2. Bitcoin
3. Decentralised AI
4. Investing in Digital Assets
5. Privacy
6. Prediction Markets

### My Current 60+ Granular Interest Terms
Here's how I propose mapping them to your 6 verticals:

---

#### **Tokenisation of Finance** ← Maps from:
- tokenised real-world assets
- tokenised securities
- regulated custody
- settlement infrastructure
- banking partnerships
- institutional custody
- stablecoins
- CBDC
- regulatory frameworks
- MiCA
- compliance modules
- KYC/AML
- tokenised securities regulation
- compliance-first technology

---

#### **Bitcoin** ← Maps from:
- Bitcoin
- Bitcoin infrastructure
- Bitcoin ETFs
- Bitcoin custody
- Lightning Network

---

#### **Decentralised AI** ← Maps from:
- AI agents
- decentralised AI
- machine learning infrastructure
- Bittensor
- AI x crypto

---

#### **Investing in Digital Assets** ← Maps from:
- venture capital
- Series A-B investing
- institutional traction
- co-investment
- TradFi-DeFi convergence
- asset management
- portfolio allocation
- institutional allocators

---

#### **Privacy** ← Maps from:
- privacy protocols
- zero-knowledge proofs
- ZK-SNARKs
- confidential computing
- private transactions

---

#### **Prediction Markets** ← Maps from:
- prediction markets
- forecasting
- Polymarket
- betting protocols

---

#### **Ambiguous Terms** (Could fit multiple verticals — need your input!)

| **My Current Tag** | **Could Be...** | **Your Preferred Vertical?** |
|-------------------|-----------------|------------------------------|
| blockchain infrastructure | Tokenisation of Finance OR Investing | ? |
| institutional DeFi | Tokenisation of Finance OR Investing | ? |
| Layer-2 scaling | Tokenisation of Finance (if finance-focused) OR Decentralised AI (if AI-focused) | ? |
| cross-chain settlement | Tokenisation of Finance | ? |
| enterprise blockchain | Tokenisation of Finance | ? |
| DeFi | Tokenisation of Finance OR Investing | ? |

---

## 4. Action Items for Jes

### ✅ Review the vertical mappings above
- Are the mappings accurate?
- Any terms I've miscategorized?
- How should I handle the ambiguous terms?

### ✅ Confirm multiple verticals allowed
- Can one person have multiple tags? (e.g., someone working on "Bitcoin privacy" = **Bitcoin** + **Privacy**?)

### ✅ Decide on sync direction
- Should I **pull** from your API (I query your directory hourly)?
- Or do you **push** to my API (you call my endpoint when someone is approved)?

### ✅ Confirm LinkedIn URL as unique ID
- This will be how we dedupe/link profiles between systems
- What if someone doesn't have LinkedIn? Use email as fallback?

---

## 5. What Happens Next

Once you confirm the mappings:
1. I'll add `seniority_tier`, `region`, `verticals` fields to my database
2. I'll build an AI classifier to auto-tag existing attendees
3. I'll create an API endpoint for syncing your 1000 Minds data into my matchmaker
4. Users will see "1000 Minds That Matter" badges in their match recommendations

---

**Questions? Adjustments?** Let me know!

— Kanyuchi
