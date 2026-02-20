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
    summary = a.ai_summary or f"{a.title} at {a.company}"
    intents = ", ".join(a.intent_tags) if a.intent_tags else "not classified"
    deal = f"{a.deal_readiness_score:.0%}" if a.deal_readiness_score else "0%"
    interests = ", ".join((a.interests or [])[:4]) or "none"
    stage = a.deal_stage or "unspecified"
    return (
        f"• {a.name} ({a.ticket_type.upper()}) — {a.title}, {a.company}\n"
        f"  Interests: {interests}\n"
        f"  Intents: {intents} | Deal Readiness: {deal} | Stage: {stage}\n"
        f"  Summary: {summary}"
    )


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

    system_prompt = f"""You are the AI Concierge for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace, Paris (June 2–3, 2026). This event brings together 2,500 decision-makers controlling $18 trillion in assets.

You help attendees:
- Discover who they should meet and why
- Prepare for specific meetings with talking points and deal structures
- Understand non-obvious connections between attendees
- Make the most of their conference time

REGISTERED ATTENDEES:
{attendee_context}

OPTIONAL AGENT TOOL CONTEXT:
{tool_context}

Guidelines:
- Be specific and actionable — reference real names, amounts, and products
- Explain WHY a connection is valuable, not just that it exists
- Suggest concrete meeting topics and potential deal structures
- Keep responses concise (3–6 sentences) unless detail is needed
- If asked who to meet, recommend 2–3 people with brief explanations"""

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
