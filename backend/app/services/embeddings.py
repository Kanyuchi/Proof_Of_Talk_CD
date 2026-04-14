import json

import numpy as np
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.constants import VALID_VERTICALS

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def build_composite_text(attendee) -> str:
    """Build a rich text blob from all attendee data for embedding."""
    parts = [
        f"Name: {attendee.name}",
        f"Title: {attendee.title}",
        f"Company: {attendee.company}",
        f"Ticket Type: {attendee.ticket_type.value if hasattr(attendee.ticket_type, 'value') else attendee.ticket_type}",
    ]

    if attendee.interests:
        parts.append(f"Interests: {', '.join(attendee.interests)}")

    if attendee.goals:
        parts.append(f"Goals: {attendee.goals}")

    if attendee.ai_summary:
        parts.append(f"Profile Summary: {attendee.ai_summary}")

    # Include enriched data highlights if available
    enriched = attendee.enriched_profile or {}
    if enriched.get("linkedin_summary"):
        parts.append(f"LinkedIn: {enriched['linkedin_summary']}")
    if enriched.get("company_description"):
        parts.append(f"Company Info: {enriched['company_description']}")
    if enriched.get("recent_activity"):
        parts.append(f"Recent Activity: {enriched['recent_activity']}")
    if enriched.get("funding_info"):
        parts.append(f"Funding: {enriched['funding_info']}")

    # The Grid B2B data — verified Web3 company intelligence
    grid = enriched.get("grid") or {}
    if grid.get("grid_description"):
        parts.append(f"Company (Grid verified): {grid['grid_description']}")
    if grid.get("grid_sector"):
        parts.append(f"Grid Sector: {grid['grid_sector']}")
    if grid.get("grid_type"):
        parts.append(f"Company Type: {grid['grid_type']}")
    grid_products = grid.get("grid_products") or []
    if grid_products:
        product_lines = [
            f"{p['name']}: {p.get('description', '')}" for p in grid_products[:3] if p.get("name")
        ]
        if product_lines:
            parts.append(f"Products/Services: {'; '.join(product_lines)}")

    if getattr(attendee, "target_companies", None):
        parts.append(f"Who they want to meet: {attendee.target_companies}")

    if attendee.vertical_tags:
        parts.append(f"Sector Verticals: {', '.join(attendee.vertical_tags)}")
    if attendee.intent_tags:
        parts.append(f"Intent Tags: {', '.join(attendee.intent_tags)}")

    icp = getattr(attendee, "inferred_customer_profile", None) or {}
    if icp.get("offers"):
        parts.append(f"Offers: {icp['offers']}")
    customer_lines = []
    for c in (icp.get("ideal_customers") or [])[:3]:
        who = c.get("who", "")
        kws = ", ".join(c.get("signal_keywords") or [])
        if who:
            customer_lines.append(f"{who} ({kws})" if kws else who)
    if customer_lines:
        parts.append(f"Ideal Customers: {'; '.join(customer_lines)}")
    partner_lines = []
    for p in (icp.get("ideal_partners") or [])[:2]:
        who = p.get("who", "")
        kws = ", ".join(p.get("signal_keywords") or [])
        if who:
            partner_lines.append(f"{who} ({kws})" if kws else who)
    if partner_lines:
        parts.append(f"Ideal Partners: {'; '.join(partner_lines)}")

    return "\n".join(parts)


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector using OpenAI text-embedding-3-small."""
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_attendee(attendee) -> list[float]:
    """Build composite text and generate embedding for an attendee."""
    text = build_composite_text(attendee)
    return await generate_embedding(text)


async def generate_ai_summary(attendee) -> str:
    """Use GPT-4o to generate a concise attendee profile summary."""
    prompt = f"""You are an AI assistant for a premium Web3 conference (Proof of Talk 2026, 2500 decision-makers, $18T AUM).

Generate a concise 2-3 sentence professional summary of this attendee that captures:
- Their role and what their organization does
- What they're actively looking for at this event
- Their deal-readiness and decision-making authority

Attendee data:
Name: {attendee.name}
Title: {attendee.title}
Company: {attendee.company}
Ticket Type: {attendee.ticket_type.value if hasattr(attendee.ticket_type, 'value') else attendee.ticket_type}
Interests: {', '.join(attendee.interests) if attendee.interests else 'Not specified'}
Goals: {attendee.goals or 'Not specified'}

Enriched data: {attendee.enriched_profile or 'None available'}

Write the summary in third person. Be specific about their investment thesis, product, or mandate. Do not use generic language."""

    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


async def classify_intents(attendee) -> list[str]:
    """Use GPT-4o to classify attendee intents into structured tags."""
    prompt = f"""Classify this conference attendee's intents into structured tags.

Attendee: {attendee.name}, {attendee.title} at {attendee.company}
Goals: {attendee.goals or 'Not specified'}
Interests: {', '.join(attendee.interests) if attendee.interests else 'Not specified'}

Return ONLY a JSON array of intent tags from this taxonomy:
- "deploying_capital" (actively investing/allocating)
- "raising_capital" (seeking funding)
- "seeking_partnerships" (business development)
- "seeking_customers" (sales pipeline)
- "regulatory_engagement" (policy/compliance discussions)
- "technology_evaluation" (assessing tech solutions)
- "deal_making" (ready to transact)
- "knowledge_exchange" (learning/sharing expertise)
- "co_investment" (seeking co-investors)
- "talent_acquisition" (hiring)

Return 2-4 most relevant tags as a JSON array. Nothing else."""

    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return ["knowledge_exchange"]


async def classify_verticals(attendee) -> list[str]:
    """Use GPT-4o to classify attendee into 1000minds sector verticals."""
    prompt = f"""Classify this conference attendee into sector verticals.

Attendee: {attendee.name}, {attendee.title} at {attendee.company}
Goals: {attendee.goals or 'Not specified'}
Interests: {', '.join(attendee.interests) if attendee.interests else 'Not specified'}
AI Summary: {attendee.ai_summary or 'Not available'}

Return ONLY a JSON array of vertical tags from this taxonomy:
- "tokenisation_of_finance" (RWA tokenisation, institutional DeFi, digital securities)
- "infrastructure_and_scaling" (L1/L2, rollups, interoperability, developer tooling)
- "decentralized_finance" (DEXs, lending, yield, stablecoins, DeFi protocols)
- "ai_depin_frontier_tech" (AI agents, DePIN, IoT, compute networks, frontier tech)
- "policy_regulation_macro" (regulation, compliance, CBDC, macro policy)
- "ecosystem_and_foundations" (protocol foundations, grants, ecosystem growth)
- "investment_and_capital_markets" (VC, fund management, capital allocation, trading)
- "culture_media_gaming" (NFTs, gaming, metaverse, media, entertainment)
- "bitcoin" (Bitcoin L2, mining, ordinals, Bitcoin-native DeFi)
- "prediction_markets" (prediction markets, information markets, betting protocols)
- "decentralized_ai" (decentralised AI, federated learning, AI DAOs, AI compute)
- "privacy" (ZK proofs, confidential computing, privacy protocols, private transactions)

Return 1-3 most relevant verticals as a JSON array. Nothing else."""

    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        tags = json.loads(raw)
        return [t for t in tags if t in VALID_VERTICALS]
    except json.JSONDecodeError:
        return []


async def infer_customer_profile(attendee) -> dict:
    """Infer an attendee's ideal customer / partner profile (ICP) using GPT-4o.

    Returns a structured dict describing who would realistically buy from,
    invest in, or partner with this attendee — used to find non-explicit
    matches when target_companies is empty.
    """
    grid = (attendee.enriched_profile or {}).get("grid") or {}
    grid_summary = ""
    if grid.get("grid_description"):
        grid_summary = (
            f"Grid Verified: {grid.get('grid_description', '')}\n"
            f"Grid Sector: {grid.get('grid_sector', '')}\n"
            f"Key Products: {', '.join(p.get('name', '') for p in (grid.get('grid_products') or [])[:5])}"
        )

    prompt = f"""You are inferring the ideal customer / partner profile (ICP) for a Web3 conference attendee.
Goal: identify who would realistically buy from, invest in, sell to, or partner with this person at Proof of Talk 2026 (2,500 decision-makers, $18T AUM).

ATTENDEE:
Name: {attendee.name}
Title: {attendee.title}
Company: {attendee.company}
Goals: {attendee.goals or 'Not specified'}
AI Summary: {attendee.ai_summary or 'Not available'}
Vertical Tags: {', '.join(attendee.vertical_tags) if attendee.vertical_tags else 'None'}
Intent Tags: {', '.join(attendee.intent_tags) if attendee.intent_tags else 'None'}
{grid_summary}

Return ONLY a JSON object with this exact shape:
{{
  "offers": "<one sentence: what this attendee/company actually provides — product, capital, expertise, regulation, etc.>",
  "ideal_customers": [
    {{
      "who": "<concrete persona — e.g. 'Sovereign wealth funds deploying into tokenised RWA'>",
      "why": "<one sentence on why they'd transact>",
      "signal_keywords": ["3-6 lowercase keywords/phrases that would appear in a matching attendee's role, goals, vertical_tags, or company description"]
    }}
  ],
  "ideal_partners": [
    {{
      "who": "<concrete partner persona>",
      "why": "<why the partnership creates value>",
      "signal_keywords": ["3-6 lowercase keywords"]
    }}
  ],
  "anti_personas": ["short list of who is NOT a fit — e.g. 'direct competitors in custody infra'"]
}}

Rules:
- 2-3 ideal_customers, 1-2 ideal_partners.
- Be SPECIFIC. "Crypto companies" is useless. "Series A DeFi protocols needing institutional custody" is useful.
- signal_keywords must be lowercase, concrete, and likely to appear in another attendee's profile text.
- If the attendee is themselves a buyer (investor, allocator, regulator), ideal_customers describes who they would buy FROM (e.g. an allocator's ideal_customers = founders raising in their thesis).
- Never invent details not implied by the data. If unsure, keep personas broad but truthful.
- Return ONLY the JSON object. No markdown, no commentary."""

    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        data.setdefault("offers", "")
        data.setdefault("ideal_customers", [])
        data.setdefault("ideal_partners", [])
        data.setdefault("anti_personas", [])
        return data
    except json.JSONDecodeError:
        return {}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
