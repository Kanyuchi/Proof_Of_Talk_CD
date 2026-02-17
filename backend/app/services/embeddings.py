import numpy as np
from openai import AsyncOpenAI
from app.core.config import get_settings

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
    import json
    try:
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return ["knowledge_exchange"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
