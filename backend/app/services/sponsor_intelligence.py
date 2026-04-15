"""
Sponsor Intelligence Service
=============================
Generates personalised intelligence reports for POT 2026 sponsors.
Uses The Grid for verified company data, pgvector for attendee relevance,
and GPT-4o for explanations with built-in overstating prevention.

Confidence scoring is computed deterministically from data completeness —
not by GPT — to prevent hallucinated confidence levels.
"""

import json
import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.grid_enrichment import enrich_from_grid

logger = logging.getLogger(__name__)
settings = get_settings()
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# ── Sponsor data (from Google Sheet: POT 2026 Sponsorship Tracker) ────────
SPONSORS = [
    {"name": "Zircuit",          "value": 50000,  "tier": "Gold",     "lead": "Karl"},
    {"name": "CertiK",          "value": 49000,  "tier": "Platinum", "lead": "Karl"},
    {"name": "BPI France",      "value": 20000,  "tier": "Silver",   "lead": "Karl"},
    {"name": "Taostats",        "value": 116000, "tier": "Diamond",  "lead": "Paul"},
    {"name": "V3V Ventures",    "value": 40000,  "tier": "Gold",     "lead": "William"},
    {"name": "Naoris Protocol", "value": 55000,  "tier": "Gold",     "lead": "William"},
    {"name": "Cryptomarkt",     "value": 15000,  "tier": "Silver",   "lead": "William"},
    {"name": "XBTO",           "value": 35000,  "tier": "Gold",     "lead": "Kate"},
    {"name": "Spectrum",        "value": 60000,  "tier": "Platinum", "lead": "Kate"},
    {"name": "Rain",           "value": 40000,  "tier": "Gold",     "lead": "Nupur"},
    {"name": "Edge & Node",    "value": 65000,  "tier": "Platinum", "lead": "Nupur"},
    {"name": "BitGo",          "value": 55000,  "tier": "Gold",     "lead": "Karl"},
    {"name": "BitMEX",         "value": 25000,  "tier": "Gold",     "lead": "Karl"},
    {"name": "Paxos",          "value": 25000,  "tier": "Silver",   "lead": "William"},
    {"name": "Morph Network",  "value": 35000,  "tier": "Gold",     "lead": "Nupur"},
    {"name": "DFG",            "value": 45000,  "tier": "Gold",     "lead": "William"},
    {"name": "Enlivex",        "value": 30000,  "tier": "Gold",     "lead": "William"},
    {"name": "SimplyTAO",      "value": 30000,  "tier": "Gold",     "lead": "William"},
    {"name": "Nexus Mutual",   "value": 30000,  "tier": "Gold",     "lead": "William"},
    {"name": "ChangeNow",      "value": 70000,  "tier": "Platinum", "lead": "William"},
    {"name": "21X",            "value": 70000,  "tier": "Platinum", "lead": "William"},
    {"name": "Teroxx",         "value": 35000,  "tier": "Gold",     "lead": "William"},
    {"name": "Holonym",        "value": 8000,   "tier": "Startup",  "lead": "William"},
    {"name": "MatterFi",       "value": 12000,  "tier": "Silver",   "lead": "William"},
]


# ── Confidence scoring (deterministic, not GPT) ──────────────────────────

def compute_match_confidence(
    attendee: dict, sponsor_has_grid: bool, similarity: float
) -> dict:
    """
    Deterministic confidence score based on data completeness.
    Returns score (0-1), label, data sources present, and missing data.
    """
    score = 0.0
    data_sources = []
    missing = []

    if sponsor_has_grid:
        score += 0.15
        data_sources.append("sponsor_grid_verified")

    if attendee.get("grid_name"):
        score += 0.10
        data_sources.append("attendee_grid_verified")
    else:
        missing.append("attendee_grid_data")

    if attendee.get("goals"):
        score += 0.15
        data_sources.append("self_reported_goals")
    else:
        missing.append("goals")

    if attendee.get("ai_summary"):
        score += 0.10
        data_sources.append("ai_profile_summary")
    else:
        missing.append("ai_summary")

    if attendee.get("intent_tags"):
        score += 0.10
        data_sources.append("ai_classified_intents")
    else:
        missing.append("intent_tags")

    if similarity > 0.3:
        score += 0.10
        data_sources.append("vector_similarity_moderate")
    if similarity > 0.5:
        score += 0.10
        data_sources.append("vector_similarity_strong")

    if (attendee.get("deal_readiness") or 0) > 0.5:
        score += 0.10
        data_sources.append("high_deal_readiness")

    if attendee.get("vertical_tags"):
        score += 0.10
        data_sources.append("sector_verticals")
    else:
        missing.append("vertical_tags")

    score = min(1.0, score)
    if score >= 0.7:
        label = "high"
    elif score >= 0.4:
        label = "medium"
    else:
        label = "low"

    return {
        "score": round(score, 2),
        "label": label,
        "data_sources": data_sources,
        "missing_data": missing,
        "grounding": {
            "sponsor_verified": sponsor_has_grid,
            "attendee_verified": bool(attendee.get("grid_name")),
            "goals_stated": bool(attendee.get("goals")),
            "sector_match": bool(attendee.get("vertical_tags")),
            "intent_known": bool(attendee.get("intent_tags")),
        },
    }


# ── Core pipeline functions ───────────────────────────────────────────────

def _build_composite_text(sponsor: dict, grid: dict | None) -> str:
    parts = [f"Company: {sponsor['name']}", f"Sponsorship Tier: {sponsor['tier']}"]
    if grid:
        if grid.get("grid_description"):
            parts.append(f"Description (Grid verified): {grid['grid_description']}")
        if grid.get("grid_description_long"):
            parts.append(f"Full Description: {grid['grid_description_long'][:300]}")
        if grid.get("grid_sector"):
            parts.append(f"Sector: {grid['grid_sector']}")
        if grid.get("grid_type"):
            parts.append(f"Company Type: {grid['grid_type']}")
        products = grid.get("grid_products") or []
        if products:
            lines = [f"{p['name']}: {p.get('description', '')}" for p in products[:5] if p.get("name")]
            parts.append(f"Products: {'; '.join(lines)}")
    else:
        parts.append("Sponsor at Proof of Talk 2026 Web3 conference")
    return "\n".join(parts)


async def _generate_embedding(text_input: str) -> list[float]:
    response = await openai_client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL, input=text_input
    )
    return response.data[0].embedding


INTERNAL_COMPANY_PATTERNS = (
    "proof of talk", "proofoftalk", "proof of talk sa",
    "xventures", "x ventures", "x-ventures", "xventures labs",
)
INTERNAL_EMAIL_DOMAINS = ("proofoftalk.io", "xventures.de", "x-ventures.de")


async def _find_relevant_attendees(
    db: AsyncSession, embedding: list[float], top_k: int = 20
) -> list[dict]:
    """Retrieve top-k attendees by cosine similarity, excluding internal staff.

    Exclusions:
      - Admin-linked attendees (existing behaviour)
      - Anyone with a company name matching PoT / XVentures internal patterns
      - Anyone whose email root domain is proofoftalk.io or xventures.de
        (note: @speaker.proofoftalk.io is NOT excluded — those are legitimate
        external speakers registered through the speaker flow)
    """
    emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
    query = text("""
        SELECT id, name, email, title, company, company_website,
               goals, ticket_type, ai_summary, vertical_tags, intent_tags,
               deal_readiness_score, enriched_profile,
               1 - (embedding <=> :embedding) as similarity
        FROM attendees
        WHERE embedding IS NOT NULL
          AND id NOT IN (
              SELECT attendee_id FROM users
              WHERE is_admin = true AND attendee_id IS NOT NULL
          )
          AND LOWER(COALESCE(TRIM(company), '')) NOT IN :internal_companies
          AND split_part(LOWER(email), '@', 2) NOT IN :internal_domains
        ORDER BY embedding <=> :embedding
        LIMIT :top_k
    """).bindparams(
        bindparam("internal_companies", expanding=True),
        bindparam("internal_domains", expanding=True),
    )
    result = await db.execute(query, {
        "embedding": emb_str,
        "top_k": top_k,
        "internal_companies": list(INTERNAL_COMPANY_PATTERNS),
        "internal_domains": list(INTERNAL_EMAIL_DOMAINS),
    })
    rows = result.fetchall()

    attendees = []
    for r in rows:
        enriched = r.enriched_profile if isinstance(r.enriched_profile, dict) else (
            json.loads(r.enriched_profile) if r.enriched_profile else {}
        )
        grid = enriched.get("grid") or {}
        attendees.append({
            "name": r.name, "email": r.email, "title": r.title or "",
            "company": r.company or "", "goals": r.goals or "",
            "ticket_type": r.ticket_type or "", "ai_summary": r.ai_summary or "",
            "vertical_tags": r.vertical_tags or [], "intent_tags": r.intent_tags or [],
            "deal_readiness": r.deal_readiness_score or 0,
            "similarity": float(r.similarity),
            "grid_name": grid.get("grid_name", ""),
            "grid_sector": grid.get("grid_sector", ""),
        })
    return attendees


async def _find_sponsor_team(db: AsyncSession, sponsor_name: str) -> list[dict]:
    pattern = f"%{sponsor_name.lower()}%"
    query = text("""
        SELECT name, email, title, company, ticket_type
        FROM attendees
        WHERE LOWER(company) LIKE :pattern OR LOWER(email) LIKE :pattern
    """)
    result = await db.execute(query, {"pattern": pattern})
    return [
        {"name": r.name, "email": r.email, "title": r.title or "",
         "company": r.company or "", "ticket_type": r.ticket_type or ""}
        for r in result.fetchall()
    ]


async def _generate_explanations(
    sponsor: dict, grid: dict | None, attendees: list[dict]
) -> list[dict]:
    """GPT-4o explanations with overstating prevention."""
    grid_context = ""
    if grid:
        products = ", ".join(p["name"] for p in (grid.get("grid_products") or [])[:5])
        grid_context = f"""
Grid Verified Company Data:
- Description: {grid.get('grid_description', 'N/A')}
- Sector: {grid.get('grid_sector', 'N/A')}
- Type: {grid.get('grid_type', 'N/A')}
- Products: {products or 'N/A'}
"""

    attendee_blocks = []
    for i, a in enumerate(attendees[:20]):
        attendee_blocks.append(
            f"Attendee {i+1}:\n"
            f"  Name: {a['name']}\n"
            f"  Title: {a['title']}\n"
            f"  Company: {a['company']}\n"
            f"  Ticket: {a['ticket_type']}\n"
            f"  Goals: {a['goals'][:200] if a['goals'] else 'NOT SPECIFIED'}\n"
            f"  AI Summary: {a['ai_summary'][:200] if a['ai_summary'] else 'N/A'}\n"
            f"  Sectors: {', '.join(a['vertical_tags'][:3]) or 'NONE'}\n"
            f"  Intent: {', '.join(a['intent_tags'][:3]) or 'NONE'}\n"
            f"  Deal Readiness: {a['deal_readiness']:.0%}\n"
            f"  Relevance Score: {a['similarity']:.3f}"
        )

    prompt = f"""You are generating a sponsor intelligence report for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace with 2,500 decision-makers.

CRITICAL RULES FOR ACCURACY:
1. ONLY cite facts that appear in the attendee data below. Do NOT infer, assume, or fabricate details.
2. If an attendee's goals are "NOT SPECIFIED", say "Goals not disclosed" — do NOT guess what they might want.
3. If sector/intent tags are empty, base relevance ONLY on their title, company, and ticket type.
4. Prefix each claim with its source: [GRID] for Grid-verified data, [GOALS] for self-reported goals, [PROFILE] for title/company, [AI-INFERRED] for anything not directly stated.
5. When information is sparse, explicitly say: "Limited profile data — relevance based on [source] only."
6. DO NOT overstate deal potential. If you cannot identify a specific, data-backed reason for a meeting, rate relevance as LOW.
7. Never claim someone "is actively seeking" or "has expressed interest in" unless their goals or intent tags explicitly say so.
8. Never invent funding amounts, mandates, or investment theses that are not in the data.

SPONSOR COMPANY: {sponsor['name']}
Sponsorship Tier: {sponsor['tier']} (€{sponsor['value']:,})
{grid_context}
CANDIDATE ATTENDEES (ranked by AI relevance):
{chr(10).join(attendee_blocks)}

For each attendee, generate a JSON entry. Return a JSON array:
[
  {{
    "attendee_index": <1-based>,
    "relevance": "HIGH" | "MEDIUM" | "LOW",
    "why_they_matter": "2-3 sentences — prefix each claim with [GRID], [GOALS], [PROFILE], or [AI-INFERRED]",
    "conversation_opener": "One specific opening topic grounded in data",
    "deal_potential": "What could realistically come from this meeting — be conservative",
    "data_quality": "rich" | "moderate" | "sparse",
    "key_evidence": ["[SOURCE] specific fact used", "..."],
    "caveats": "Any warnings about sparse data or inferred connections — leave empty string if data is rich"
  }}
]

Return ONLY the JSON array. No markdown."""

    response = await openai_client.chat.completions.create(
        model=settings.OPENAI_RERANK_MODEL or settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.15,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse sponsor explanation response")
        return []


# ── Main entry point ──────────────────────────────────────────────────────

async def run_sponsor_report(
    sponsor_name: str,
    db: AsyncSession,
    top_k: int = 20,
    identify_team: bool = True,
) -> dict:
    """Full pipeline: Grid → Embed → pgvector → GPT-4o → report with confidence."""

    # Find sponsor
    sponsor = next((s for s in SPONSORS if s["name"].lower() == sponsor_name.lower()), None)
    if not sponsor:
        # Fuzzy match
        sponsor = next((s for s in SPONSORS if sponsor_name.lower() in s["name"].lower()), None)
    if not sponsor:
        return {"error": f"Sponsor '{sponsor_name}' not found"}

    # 1. Query The Grid
    grid = await enrich_from_grid(sponsor["name"])

    # 2. Build composite + embed
    composite = _build_composite_text(sponsor, grid)
    embedding = await _generate_embedding(composite)

    # 3. Find relevant attendees
    attendees = await _find_relevant_attendees(db, embedding, top_k=top_k)

    # 4. Identify team members
    team_members = []
    if identify_team:
        team_members = await _find_sponsor_team(db, sponsor["name"])

    # 5. Compute confidence for each attendee (deterministic)
    sponsor_has_grid = grid is not None
    for a in attendees:
        a["confidence"] = compute_match_confidence(a, sponsor_has_grid, a["similarity"])

    # 6. GPT-4o explanations with overstating prevention
    explanations = await _generate_explanations(sponsor, grid, attendees)

    # 7. Merge confidence into explanations
    for exp in explanations:
        idx = exp.get("attendee_index", 1) - 1
        if 0 <= idx < len(attendees):
            exp["confidence"] = attendees[idx]["confidence"]

    # Summary stats
    high_count = sum(1 for e in explanations if e.get("relevance") == "HIGH")
    medium_count = sum(1 for e in explanations if e.get("relevance") == "MEDIUM")
    low_count = len(explanations) - high_count - medium_count

    return {
        "sponsor": sponsor,
        "grid_data": {
            "found": grid is not None,
            "name": grid.get("grid_name") if grid else None,
            "sector": grid.get("grid_sector") if grid else None,
            "description": grid.get("grid_description") if grid else None,
            "products": [p["name"] for p in (grid.get("grid_products") or [])[:5]] if grid else [],
        },
        "attendees": attendees[:top_k],
        "explanations": explanations,
        "team_members": team_members,
        "summary": {
            "total_targets": len(explanations),
            "high_relevance": high_count,
            "medium_relevance": medium_count,
            "low_relevance": low_count,
            "team_attending": len(team_members),
            "avg_confidence": round(
                sum(a["confidence"]["score"] for a in attendees[:len(explanations)]) / max(len(explanations), 1), 2
            ),
        },
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top_k": top_k,
            "disclaimer": "This report combines Grid-verified data, self-reported attendee information, and AI-generated analysis. Fields marked [AI-INFERRED] should be verified before acting on them.",
        },
    }
