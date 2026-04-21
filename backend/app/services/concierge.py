"""AI Concierge service with optional agentic orchestration."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.attendee import Attendee

settings = get_settings()
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def _list_attendees(db: AsyncSession) -> list[Attendee]:
    result = await db.execute(select(Attendee))
    return result.scalars().all()


def _brief_attendee_line(a: Attendee) -> str:
    intents = ", ".join(a.intent_tags) if a.intent_tags else "none"
    deal = f"{a.deal_readiness_score:.0%}" if a.deal_readiness_score else "0%"
    interests = ", ".join((a.interests or [])[:4]) or "none"
    stage = a.deal_stage or "unspecified"
    verticals = ", ".join(a.vertical_tags) if a.vertical_tags else "none"
    goals = a.goals or "none"
    title = a.title or "not provided"

    # Flag data completeness so the AI knows when to be cautious
    has_interests = bool(a.interests)
    has_goals = bool(a.goals and a.goals.strip())
    has_intents = bool(a.intent_tags)
    has_title = bool(a.title and a.title.strip())
    completeness = sum([has_interests, has_goals, has_intents, has_title])
    if completeness <= 1:
        quality = "SPARSE — treat AI summary with caution, do NOT present inferred details as facts"
    elif completeness <= 2:
        quality = "PARTIAL"
    else:
        quality = "GOOD"

    lines = [
        f"• {a.name} ({a.ticket_type.upper()}) — {title}, {a.company}",
        f"  [VERIFIED] Title: {title} | Company: {a.company}",
        f"  [VERIFIED] Interests: {interests}",
        f"  [VERIFIED] Goals: {goals}",
        f"  [VERIFIED] Verticals: {verticals}",
        f"  [VERIFIED] Intents: {intents} | Deal Readiness: {deal} | Stage: {stage}",
        f"  Data quality: {quality}",
    ]
    # Only include AI summary for profiles with enough real data to cross-check against
    if a.ai_summary and completeness >= 2:
        lines.append(f"  [AI-INFERRED] Summary: {a.ai_summary}")
    elif completeness <= 1:
        lines.append(f"  ⚠ No reliable summary available — ONLY use the VERIFIED fields above.")
    return "\n".join(lines)


def _build_attendee_context(attendees: list[Attendee]) -> str:
    return "\n\n".join(_brief_attendee_line(a) for a in attendees)


async def _agent_plan(message: str, history: list[dict], attendees: list[Attendee]) -> dict[str, Any]:
    """Use a lightweight controller model to classify user intent and filters."""
    attendee_catalog = "\n".join(
        f"- {a.name} | {a.title} @ {a.company} | intents: {', '.join(a.intent_tags or [])}"
        for a in attendees[:80]
    )
    prompt = f"""You are a routing controller for a conference concierge.

Classify the user request and extract lightweight filters.

Return ONLY JSON with this schema:
{{
  "intent": "who_to_meet" | "meeting_prep" | "sector_discovery" | "general",
  "sector": "<string or null>",
  "deal_stage": "<string or null>",
  "ticket_type": "<vip|speaker|sponsor|delegate|null>",
  "target_name": "<string or null>",
  "response_style": "concise" | "detailed"
}}

Recent chat history:
{history[-5:]}

User message:
{message}

Attendee catalog:
{attendee_catalog}
"""
    response = await _get_client().chat.completions.create(
        model=settings.OPENAI_AGENT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "intent": "general",
            "sector": None,
            "deal_stage": None,
            "ticket_type": None,
            "target_name": None,
            "response_style": "concise",
        }


def _apply_tool_filters(attendees: list[Attendee], plan: dict[str, Any]) -> list[Attendee]:
    """Deterministic tool step: filter attendees from controller hints."""
    sector = (plan.get("sector") or "").strip().lower()
    deal_stage = (plan.get("deal_stage") or "").strip().lower()
    ticket_type = (plan.get("ticket_type") or "").strip().lower()
    target_name = (plan.get("target_name") or "").strip().lower()

    filtered = attendees
    if ticket_type:
        filtered = [
            a
            for a in filtered
            if str(a.ticket_type.value if hasattr(a.ticket_type, "value") else a.ticket_type).lower() == ticket_type
        ]
    if deal_stage:
        filtered = [a for a in filtered if (a.deal_stage or "").strip().lower() == deal_stage]
    if sector:
        filtered = [
            a
            for a in filtered
            if sector in " ".join((a.interests or [])).lower()
            or sector in (a.ai_summary or "").lower()
            or sector in " ".join(a.vertical_tags or []).lower()
        ]
    if target_name:
        filtered = [a for a in filtered if target_name in a.name.lower()]
    return filtered[:8]


async def concierge_chat(
    message: str,
    history: list[dict],
    db: AsyncSession,
) -> str:
    """Run one turn of concierge conversation with optional agentic orchestration."""
    attendees = await _list_attendees(db)
    attendee_context = _build_attendee_context(attendees)

    if settings.AI_AGENT_ENABLED:
        plan = await _agent_plan(message, history, attendees)
        filtered = _apply_tool_filters(attendees, plan)
        tool_context = (
            "Agent Plan:\n"
            f"{json.dumps(plan, ensure_ascii=True)}\n\n"
            "Tool Result (filtered attendees):\n"
            + "\n\n".join(_brief_attendee_line(a) for a in filtered)
        )
    else:
        tool_context = "Agentic controller disabled."

    system_prompt = f"""You are the AI Concierge for Proof of Talk 2026 — a friendly, knowledgeable assistant helping attendees navigate an exclusive Web3 conference at the Louvre Palace, Paris (June 2–3, 2026). 2,500 decision-makers, $18 trillion in assets.

You help attendees discover who to meet, prepare for meetings, and spot non-obvious connections.

CRITICAL ACCURACY RULES:
1. ONLY cite facts that appear in the REGISTERED ATTENDEES data below. Never invent interests, goals, deal sizes, or connections.
2. If an attendee's interests or summary say "not classified" or are generic, say "their specific goals aren't listed" — do NOT guess what they might want.
3. Tag each claim with its source: [PROFILE] for title/company, [GOALS] for self-reported interests/goals, [AI-INFERRED] for anything from the AI summary.
4. Never claim someone "is actively seeking" or "wants to" unless their interests, goals, or intent tags explicitly say so.
5. If you cannot find a relevant attendee for the user's request, say so honestly — do not force a weak recommendation.
6. Never fabricate company products, funding amounts, investment theses, or mandates that are not in the data.
7. When information is sparse for an attendee, explicitly note: "Limited profile data — based on [PROFILE] only."

REGISTERED ATTENDEES:
{attendee_context}

OPTIONAL AGENT TOOL CONTEXT:
{tool_context}

Response style — conversational and chat-friendly:
- Write like a smart colleague messaging you, not a report
- Keep it SHORT — 2–4 sentences per person you recommend, no walls of text
- Use **bold** for names and companies only
- Do NOT use ### headers or section titles — just flow naturally
- When recommending people, use this pattern (one blank line between each):
  **Name** — Title, Company
  [1-2 sentences: why this connection matters for the user specifically, with source tags]
- Limit recommendations to 2–3 people unless the user asks for more
- Be specific — reference real names, deal sizes, products, verticals FROM THE DATA ONLY
- Explain WHY a connection is valuable, not just that it exists
- Suggest a concrete opener or talking point when relevant
- End with a short follow-up question or offer ("Want me to dig into any of these?" or "I can help you prep for that meeting")
- Never start with "Great question!" or similar filler"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    response = await _get_client().chat.completions.create(
        model=settings.OPENAI_REASONING_MODEL or settings.OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=700,
    )
    return response.choices[0].message.content.strip()
