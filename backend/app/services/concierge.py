"""AI Concierge service — GPT-4o powered assistant for attendee discovery and meeting prep."""
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.models.attendee import Attendee

settings = get_settings()
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def build_attendee_context(db: AsyncSession) -> str:
    """Summarise all attendees into a compact text block for the system prompt."""
    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()

    lines = []
    for a in attendees:
        summary = a.ai_summary or f"{a.title} at {a.company}"
        intents = ", ".join(a.intent_tags) if a.intent_tags else "not classified"
        deal = f"{a.deal_readiness_score:.0%}" if a.deal_readiness_score else "0%"
        interests = ", ".join(a.interests[:4]) if a.interests else "none"
        lines.append(
            f"• {a.name} ({a.ticket_type.upper()}) — {a.title}, {a.company}\n"
            f"  Interests: {interests}\n"
            f"  Intents: {intents} | Deal Readiness: {deal}\n"
            f"  Summary: {summary}"
        )

    return "\n\n".join(lines)


async def concierge_chat(
    message: str,
    history: list[dict],
    db: AsyncSession,
) -> str:
    """Run one turn of the concierge conversation and return the AI reply."""
    attendee_context = await build_attendee_context(db)

    system_prompt = f"""You are the AI Concierge for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace, Paris (June 2–3, 2026). This event brings together 2,500 decision-makers controlling $18 trillion in assets.

You help attendees:
- Discover who they should meet and why
- Prepare for specific meetings with talking points and deal structures
- Understand non-obvious connections between attendees
- Make the most of their conference time

REGISTERED ATTENDEES:
{attendee_context}

Guidelines:
- Be specific and actionable — reference real names, amounts, and products
- Explain WHY a connection is valuable, not just that it exists
- Suggest concrete meeting topics and potential deal structures
- Keep responses concise (3–6 sentences) unless detail is needed
- If asked who to meet, recommend 2–3 people with brief explanations"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()
