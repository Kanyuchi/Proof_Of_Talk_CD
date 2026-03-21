# 1000 Minds ↔ POT Matchmaker: Taxonomy Alignment

**Date:** March 17, 2026
**Status:** Schema alignment required before integration

---

## Jes's 1000 Minds Taxonomy

### 1. Seniority Tiers
- C-Level
- Founder
- GP (General Partner)
- CIO (Chief Investment Officer)
- VP
- Director
- Head of
- Partner

### 2. Regions
- All Regions (Default)
- North America
- Europe
- Asia
- Middle East
- Global

### 3. Primary Verticals
- Tokenisation of Finance
- Bitcoin
- Decentralised AI
- Investing in Digital Assets
- Privacy
- Prediction Markets

---

## Current POT Matchmaker Schema

### Relevant Attendee Fields
```python
title: str                                    # Free text (e.g., "CEO", "Director of Digital Assets")
interests: list[str]                          # Free text array (e.g., ["DeFi", "tokenised real-world assets"])
preferred_geographies: list[str]              # Free text array (e.g., ["Europe", "Middle East"])
```

**Current State:**
- ✅ `preferred_geographies` → can map to Jes's **Regions**
- ⚠️ `interests` → loosely maps to **Verticals**, but not standardized
- ❌ No dedicated field for **Seniority Tiers**

---

## Proposed Mapping Strategy

### Option A: Add New Standardized Fields (Recommended)

Add to `Attendee` model:
```python
# 1000 Minds integration fields
seniority_tier: str | None                    # Maps to Jes's Seniority Tiers
region: str | None                            # Maps to Jes's Regions (single primary region)
verticals: list[str]                          # Maps to Jes's Primary Verticals (standardized list)

# Keep existing flexible fields for backward compatibility
interests: list[str]                          # User's free-text interests (backward compat)
preferred_geographies: list[str]              # User's preferred geographies (backward compat)
```

**Benefits:**
- Clean separation: standardized 1000 Minds data vs. user-provided data
- Backward compatible with existing attendees
- Frontend can offer dropdowns for `verticals`/`region`/`seniority_tier` while keeping free-text `interests`

**Data Flow:**
1. User registers → fills free-text `interests` + `preferred_geographies`
2. If promoted to 1000 Minds directory → admin/AI maps to standardized `verticals` + `region` + `seniority_tier`
3. Matchmaker uses both: standardized fields for filtering + free-text for embeddings

---

### Option B: Normalize Existing Fields (Migration Required)

Update existing fields to use controlled vocabulary:
```python
title: str                                    # Free text (no change)
seniority_tier: str | None                    # NEW: extracted/classified from title
interests: list[str]                          # Constrain to Jes's 6 verticals
preferred_geographies: list[str]              # Constrain to Jes's 5 regions
```

**Migration needed:**
- Run AI classifier to extract `seniority_tier` from existing `title` fields
- Map existing `interests` → standardized `verticals` (fuzzy match + manual review)
- Map existing `preferred_geographies` → standardized `regions`

**Drawback:** Loses flexibility for non-1000 Minds attendees

---

## Recommended Approach: **Option A (Dual Schema)**

### Schema Changes

#### 1. Add to `backend/app/models/attendee.py`:
```python
class SeniorityTier(str, enum.Enum):
    C_LEVEL = "C-Level"
    FOUNDER = "Founder"
    GP = "GP"
    CIO = "CIO"
    VP = "VP"
    DIRECTOR = "Director"
    HEAD_OF = "Head of"
    PARTNER = "Partner"

class Region(str, enum.Enum):
    ALL_REGIONS = "All Regions"
    NORTH_AMERICA = "North America"
    EUROPE = "Europe"
    ASIA = "Asia"
    MIDDLE_EAST = "Middle East"
    GLOBAL = "Global"

class Vertical(str, enum.Enum):
    TOKENISATION_OF_FINANCE = "Tokenisation of Finance"
    BITCOIN = "Bitcoin"
    DECENTRALISED_AI = "Decentralised AI"
    INVESTING_IN_DIGITAL_ASSETS = "Investing in Digital Assets"
    PRIVACY = "Privacy"
    PREDICTION_MARKETS = "Prediction Markets"

class Attendee(Base):
    # ... existing fields ...

    # 1000 Minds standardized taxonomy
    seniority_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verticals: Mapped[list] = mapped_column(ARRAY(String), default=list)  # Standardized

    # 1000 Minds directory fields
    is_1000_minds: Mapped[bool] = mapped_column(Boolean, default=False)
    contribution_to_digital_assets: Mapped[str | None] = mapped_column(Text, nullable=True)
    directory_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    nominated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nominated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nomination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
```

#### 2. Update embedding pipeline (`backend/app/services/embeddings.py`):
```python
def build_composite_text(attendee: Attendee) -> str:
    parts = [
        f"Name: {attendee.name}",
        f"Title: {attendee.title}",
        f"Company: {attendee.company}",
    ]

    # Add standardized 1000 Minds fields if present
    if attendee.seniority_tier:
        parts.append(f"Seniority: {attendee.seniority_tier}")
    if attendee.region:
        parts.append(f"Region: {attendee.region}")
    if attendee.verticals:
        parts.append(f"Verticals: {', '.join(attendee.verticals)}")
    if attendee.contribution_to_digital_assets:
        parts.append(f"Contribution: {attendee.contribution_to_digital_assets}")

    # Add user-provided fields
    if attendee.interests:
        parts.append(f"Interests: {', '.join(attendee.interests)}")
    if attendee.goals:
        parts.append(f"Goals: {attendee.goals}")

    # ... rest of enrichment data
```

#### 3. Update matching pipeline to boost 1000 Minds members:
```python
# In matching.py
if candidate.is_1000_minds:
    score *= 1.2  # 20% boost for directory members
```

---

## Next Steps

1. **Align with Jes:** Confirm this approach works for data sync
2. **Database migration:** Add new fields to `Attendee` model (Alembic)
3. **API updates:**
   - Add `/api/directory` endpoints (read 1000 Minds members)
   - Add `/api/directory/nominate` (submit nomination)
   - Update `/api/attendees/create` to accept new fields
4. **Frontend updates:**
   - Dropdowns for `seniority_tier`, `region`, `verticals` (powered by enums)
   - Badge display for `is_1000_minds` members in match results
5. **Data sync:** Build API client to pull Jes's directory data → populate matchmaker

---

## Questions for Jes

1. **Data format:** How is your directory data stored? (Airtable, Firebase, custom DB, JSON API?)
2. **Sync frequency:** Should matchmaker pull from your API hourly/daily, or do you push updates via webhook?
3. **Nomination approval:** Who approves nominations? Should approved nominees auto-create in matchmaker as VIP attendees?
4. **LinkedIn URL:** Confirm this is your unique identifier (we'll use it to dedupe/link profiles)
5. **Public vs. private:** What fields are public (directory) vs. internal-only (matchmaker enrichment)?

---

**Prepared by:** Kanyuchi
**For discussion with:** Jes (1000 Minds builder)
