"""AI Concierge service with optional agentic orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.attendee import Attendee

settings = get_settings()
_client: AsyncOpenAI | None = None

# Fields the concierge will proactively offer to draft, in priority order.
# Higher-impact fields (those that move match quality most) come first.
# `photo_url` is a non-GPT nudge — last priority because it doesn't change
# match quality, but useful for recognition on the day. It bypasses the
# < 80% completeness gate (see select_next_field_to_offer).
OFFERABLE_FIELDS: tuple[str, ...] = (
    "goals", "target_companies", "interests", "photo_url",
)

# Fields that bypass the completeness gate — they're worth offering even
# to a near-complete profile because they don't compete with GPT drafts.
GATE_BYPASS_FIELDS: frozenset[str] = frozenset({"photo_url"})

# Six fields used to compute profile completeness %. `title` and `company`
# are in the denominator (they raise the baseline for users who already
# have them) but NOT in OFFERABLE_FIELDS (they come from registration /
# Extasy and aren't appropriate to GPT-generate).
COMPLETENESS_FIELDS: tuple[str, ...] = (
    "goals", "target_companies", "interests",
    "title", "company", "photo_url",
)

# < 80% complete triggers the proactive offer. With 6 fields that's
# 4-or-fewer filled (i.e. at least 2 missing).
COMPLETENESS_THRESHOLD = 0.80

# Re-eligibility for a declined field. After 30 days the offer can fire
# again — gives the user space to fill it themselves, then nudges later.
DECLINE_COOLDOWN_DAYS = 30


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ── Profile data quality + offer selection ─────────────────────────────

def profile_data_quality(a: Attendee) -> Literal["SPARSE", "PARTIAL", "GOOD"]:
    """Single source of truth for the SPARSE/PARTIAL/GOOD bucket.

    Used by the [VERIFIED]-line builder in _brief_attendee_line AND by
    draft_field_candidates so the anti-hallucination posture stays in sync.
    """
    completeness = sum([
        bool(a.interests),
        bool(a.goals and a.goals.strip()),
        bool(a.intent_tags),
        bool(a.title and a.title.strip()),
    ])
    if completeness <= 1:
        return "SPARSE"
    if completeness <= 2:
        return "PARTIAL"
    return "GOOD"


def _field_is_empty(attendee: Attendee, field: str) -> bool:
    val = getattr(attendee, field, None)
    if val is None:
        return True
    if isinstance(val, str):
        return not val.strip()
    if isinstance(val, list):
        return len(val) == 0
    return False


def compute_completeness_pct(attendee: Attendee) -> int:
    """Returns 0–100. Denominator is COMPLETENESS_FIELDS (6 fields)."""
    filled = sum(0 if _field_is_empty(attendee, f) else 1 for f in COMPLETENESS_FIELDS)
    return round(100 * filled / len(COMPLETENESS_FIELDS))


def _field_prompts_state(attendee: Attendee) -> dict[str, dict[str, Any]]:
    enriched = attendee.enriched_profile or {}
    return enriched.get("field_prompts", {}) or {}


def _was_declined_recently(state_entry: dict[str, Any]) -> bool:
    if state_entry.get("state") != "declined":
        return False
    raw = state_entry.get("last_offered_at")
    if not raw:
        return False
    try:
        last = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last < timedelta(days=DECLINE_COOLDOWN_DAYS)


def select_next_field_to_offer(attendee: Attendee) -> str | None:
    """Return the next field worth offering, or None if no offer should fire.

    Logic:
      - Walk OFFERABLE_FIELDS in priority order:
          * skip fields that are already non-empty
          * skip fields declined within DECLINE_COOLDOWN_DAYS
      - GPT-drafted fields (goals / target_companies / interests) only fire
        when overall completeness is < 80%. The photo_url nudge bypasses
        that gate — at 5/6 = 83% with only the photo missing, we still
        nudge because it doesn't compete with a GPT draft.
      - Return the first eligible field, or None if nothing qualifies.
    """
    completeness = compute_completeness_pct(attendee)
    under_threshold = completeness < int(COMPLETENESS_THRESHOLD * 100)
    prompts = _field_prompts_state(attendee)
    for field in OFFERABLE_FIELDS:
        if not _field_is_empty(attendee, field):
            continue
        entry = prompts.get(field) or {}
        if _was_declined_recently(entry):
            continue
        if field not in GATE_BYPASS_FIELDS and not under_threshold:
            continue
        return field
    return None


# ── GPT-driven candidate drafting ──────────────────────────────────────

_FIELD_PROMPTS: dict[str, str] = {
    "goals": (
        "Draft 2-3 specific conference goals this attendee might want at Proof "
        "of Talk 2026 (a Web3 event of 2,500 decision-makers at the Louvre, "
        "Paris). Each goal should be concrete and action-oriented (e.g. "
        "'Meet 5 LPs interested in early-stage Web3 infrastructure funds' "
        "or 'Find 2-3 design partners for our institutional-custody product'). "
        "Goals should match the attendee's seniority and role — don't suggest "
        "junior tactics for a CEO, or strategic-partnership goals for a junior IC."
    ),
    "target_companies": (
        "Suggest 2-3 specific companies / company-types this attendee should "
        "prioritise meeting, given their role and what they appear to be "
        "working on. Be specific (real company names where you can ground them "
        "in the attendee's context); otherwise describe the company type "
        "precisely (e.g. 'Tier-1 EU crypto exchanges with PSP licences')."
    ),
    "interests": (
        "Suggest 2-3 Web3 sectors or topics this attendee likely follows "
        "professionally. Be specific — prefer 'Restaking infrastructure' or "
        "'EU MiCA compliance' over generic 'DeFi' or 'crypto regulation'. "
        "Return them as a list of short interest phrases (each ≤ 6 words)."
    ),
}


def _context_for_drafting(a: Attendee) -> str:
    enriched = a.enriched_profile or {}
    linkedin = (enriched.get("linkedin") or {}) if isinstance(enriched, dict) else {}
    headline = linkedin.get("headline") or ""
    about = linkedin.get("about") or ""
    verticals = ", ".join(a.vertical_tags or []) or "none"
    summary = a.ai_summary or ""
    lines = [
        f"Name: {a.name}",
        f"Title: {a.title or 'unknown'}",
        f"Company: {a.company or 'unknown'}",
        f"Verticals: {verticals}",
    ]
    if headline:
        lines.append(f"LinkedIn headline: {headline}")
    if about:
        lines.append(f"LinkedIn about (truncated): {about[:400]}")
    if summary:
        lines.append(f"AI summary: {summary}")
    if a.goals:
        lines.append(f"Existing goals: {a.goals}")
    if a.interests:
        lines.append(f"Existing interests: {', '.join(a.interests)}")
    if a.target_companies:
        lines.append(f"Existing target companies: {a.target_companies}")
    return "\n".join(lines)


async def draft_field_candidates(field: str, attendee: Attendee) -> tuple[list[str], bool]:
    """Ask GPT-4o for 2-3 draft values for `field`. Returns (candidates, is_sparse).

    - GOOD/PARTIAL profile: 3 candidates grounded in profile + LinkedIn context.
    - SPARSE profile: 2 generic "starting point" candidates with a relaxed prompt.
    - Empty / malformed model response: raises ValueError so the route can 500.
    """
    if field not in _FIELD_PROMPTS:
        raise ValueError(f"Unsupported field: {field}")

    quality = profile_data_quality(attendee)
    is_sparse = quality == "SPARSE"
    n_candidates = 2 if is_sparse else 3
    sparse_note = (
        "\n\nIMPORTANT: profile data is limited. Mark these as starting "
        "points — they should be generic enough that the user can rewrite "
        "freely. Do NOT invent specifics (fund sizes, products, theses) "
        "you cannot ground in the input."
        if is_sparse else ""
    )

    user_prompt = (
        f"{_FIELD_PROMPTS[field]}\n\n"
        f"Return {n_candidates} candidates as JSON: "
        f'{{"candidates": [{", ".join(["\"...\"" for _ in range(n_candidates)])}]}}.'
        f"{sparse_note}\n\n"
        f"Attendee profile:\n{_context_for_drafting(attendee)}"
    )

    response = await _get_client().chat.completions.create(
        model=settings.OPENAI_REASONING_MODEL or settings.OPENAI_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You draft concise, plausible profile-field suggestions for "
                    "attendees of a high-end Web3 conference. Be specific where the "
                    "input supports it; be generic where it doesn't. Never invent "
                    "facts (companies, products, fund sizes) that aren't grounded "
                    "in the input. Return ONLY the JSON object — no prose."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        candidates = data.get("candidates") or []
        cleaned = [str(c).strip() for c in candidates if str(c).strip()]
    except (json.JSONDecodeError, TypeError):
        raise ValueError(f"Could not parse GPT draft response: {raw[:200]}")
    if not cleaned:
        raise ValueError("GPT returned no usable candidates")
    return cleaned[:n_candidates], is_sparse


# ── Persistence helpers ────────────────────────────────────────────────

def mark_field_prompt(
    attendee: Attendee,
    field: str,
    state: Literal["accepted", "declined"],
) -> None:
    """Record an offer outcome on enriched_profile.field_prompts.{field}.

    Mutates a JSONB dict on the attendee row. The caller must commit. We
    rebuild the dict (rather than in-place edit) so SQLAlchemy's JSONB
    change tracking notices — same posture as the earlier mutation-fix
    work documented in whats_next.md.
    """
    enriched = dict(attendee.enriched_profile or {})
    prompts = dict(enriched.get("field_prompts") or {})
    prompts[field] = {
        "state": state,
        "last_offered_at": datetime.now(timezone.utc).isoformat(),
    }
    enriched["field_prompts"] = prompts
    attendee.enriched_profile = enriched


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

    # Flag data completeness so the AI knows when to be cautious.
    # profile_data_quality() is the single source of truth — also used by
    # draft_field_candidates() so the SPARSE posture stays in sync.
    bucket = profile_data_quality(a)
    if bucket == "SPARSE":
        quality = "SPARSE — treat AI summary with caution, do NOT present inferred details as facts"
    else:
        quality = bucket
    completeness = 4 if bucket == "GOOD" else (2 if bucket == "PARTIAL" else 1)

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


# Hard cap on how many attendee brief-lines get embedded in the final concierge
# prompt. The full pool (~830 rows × ~180 tokens) overflowed GPT-4o's 128k
# window (observed 147k tokens → 400 context_length_exceeded → 500 to the user).
# 80 relevant rows is plenty for a 2-3 person recommendation and leaves ample
# headroom for the system prompt, chat history, and the response.
MAX_PROMPT_ATTENDEES = 80


def _select_context_attendees(
    attendees: list[Attendee], filtered: list[Attendee]
) -> list[Attendee]:
    """Pick the attendees to embed in the final prompt, capped to
    MAX_PROMPT_ATTENDEES. Prefer the agent-filtered (relevant) subset; fall back
    to a capped slice of the full list when the filter produced nothing."""
    chosen = filtered if filtered else attendees
    return chosen[:MAX_PROMPT_ATTENDEES]


def _build_attendee_context(attendees: list[Attendee]) -> str:
    return "\n\n".join(_brief_attendee_line(a) for a in attendees)


async def _agent_plan(message: str, history: list[dict], attendees: list[Attendee]) -> dict[str, Any]:
    """Use a lightweight controller model to classify user intent and filters."""
    attendee_catalog = "\n".join(
        f"- {a.name} | {a.title} @ {a.company} | intents: {', '.join(a.intent_tags or [])}"
        for a in attendees[:250]  # raised from 80 — full attendee list is ~330, fits comfortably
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

    if settings.AI_AGENT_ENABLED:
        plan = await _agent_plan(message, history, attendees)
        filtered = _apply_tool_filters(attendees, plan)
        # The filtered subset IS the relevant context — embedding it once (capped)
        # avoids the old double-inclusion (filtered lines here + the full ~830-row
        # dump below) that blew past GPT-4o's 128k window.
        context_attendees = _select_context_attendees(attendees, filtered)
        tool_context = (
            "Agent Plan:\n"
            f"{json.dumps(plan, ensure_ascii=True)}"
        )
    else:
        context_attendees = _select_context_attendees(attendees, [])
        tool_context = "Agentic controller disabled."

    attendee_context = _build_attendee_context(context_attendees)

    system_prompt = f"""You are the AI Concierge for Proof of Talk 2026 — a friendly, knowledgeable assistant helping attendees navigate an exclusive Web3 conference at the Louvre Palace, Paris (June 2–3, 2026). 2,500 decision-makers, $18 trillion in assets.

You help attendees discover who to meet, prepare for meetings, and spot non-obvious connections.

CRITICAL ACCURACY RULES:
1. ONLY cite facts that appear in the REGISTERED ATTENDEES data below. Never invent interests, goals, deal sizes, or connections.
2. If an attendee's interests or summary say "not classified" or are generic, say "their specific goals aren't listed" — do NOT guess what they might want.
3. **Tag each claim with the EXACT source — strict, no overlap:**
   - `[PROFILE]` ONLY for facts pulled from the [VERIFIED] Title or [VERIFIED] Company lines (job title, company name)
   - `[GOALS]` ONLY for content quoted from the [VERIFIED] Goals or [VERIFIED] Interests lines (the attendee's own words)
   - `[VERTICALS]` ONLY for items in the [VERIFIED] Verticals line
   - `[INTENTS]` ONLY for items in the [VERIFIED] Intents line (deploying_capital, seeking_partnerships, etc) and the Deal Readiness percent
   - `[AI-INFERRED]` for ANYTHING that comes from the AI Summary line, OR any inference you draw across fields. **If you're unsure which tag applies, default to [AI-INFERRED] — never use [PROFILE] or [GOALS] for inferred content.**
4. Never claim someone "is actively seeking" or "wants to" unless their interests, goals, or intent tags explicitly say so.
5. If you cannot find a relevant attendee for the user's request, say so honestly — do not force a weak recommendation.
6. Never fabricate company products, funding amounts, investment theses, or mandates that are not in the data.
7. When information is sparse for an attendee (Data quality: SPARSE), explicitly note: "Limited profile data — based on title/company only" and tag claims [PROFILE] only.
8. Deal-readiness percentages and intent tags come from the AI classifier — tag them [INTENTS], NOT [PROFILE].

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
