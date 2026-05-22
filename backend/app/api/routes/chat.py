import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_auth
from app.core.limiter import limiter
from app.models.attendee import Attendee
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    DeclinePromptRequest,
    DraftFieldRequest,
    DraftFieldResponse,
    ProfilePromptResponse,
    SaveFieldRequest,
)
from app.services.concierge import (
    compute_completeness_pct,
    concierge_chat,
    draft_field_candidates,
    mark_field_prompt,
    profile_data_quality,
    select_next_field_to_offer,
)
from app.services.profile_pipeline import refresh_profile_matches

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# Keep last N exchanges in the prompt so prompt-cost stays bounded; older
# turns still live in chat_messages and can be browsed via GET /history.
HISTORY_WINDOW = 12


@router.get("/history")
async def chat_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Return the authenticated attendee's persisted concierge history (oldest first)."""
    if not user.attendee_id:
        return {"messages": []}
    rows = (await db.execute(sa_text("""
        SELECT role, content, created_at
        FROM chat_messages
        WHERE attendee_id = :aid
        ORDER BY created_at ASC, id ASC
    """), {"aid": user.attendee_id})).mappings().all()
    return {"messages": [dict(r) for r in rows]}


@router.delete("/history")
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Wipe persisted concierge history for the authenticated attendee."""
    if not user.attendee_id:
        return {"deleted": 0}
    res = await db.execute(
        sa_text("DELETE FROM chat_messages WHERE attendee_id = :aid"),
        {"aid": user.attendee_id},
    )
    await db.commit()
    return {"deleted": res.rowcount or 0}


@router.post("/concierge", response_model=ChatResponse)
@limiter.limit("20/hour")
async def chat_concierge(
    request: Request,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """AI Concierge — ask about who to meet, meeting prep, and attendee discovery.

    Persists each exchange to chat_messages so the user can resume across
    sessions. The prompt-window (last HISTORY_WINDOW turns) is rebuilt
    server-side from the DB on each request, so the client doesn't need
    to keep state and can't bloat the prompt with stale context.
    """
    aid = user.attendee_id

    # Prefer server-side history if attendee is signed in; fall back to
    # client-supplied history for unauthenticated/legacy callers.
    if aid:
        rows = (await db.execute(sa_text("""
            SELECT role, content FROM chat_messages
            WHERE attendee_id = :aid
            ORDER BY created_at DESC, id DESC
            LIMIT :n
        """), {"aid": aid, "n": HISTORY_WINDOW})).mappings().all()
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    else:
        history = [{"role": m.role, "content": m.content} for m in data.history]

    response = await concierge_chat(
        message=data.message,
        history=history,
        db=db,
    )

    # Persist exchange (only when we know who's chatting)
    if aid:
        await db.execute(
            sa_text("INSERT INTO chat_messages (attendee_id, role, content) VALUES (:aid, 'user', :c)"),
            {"aid": aid, "c": data.message},
        )
        await db.execute(
            sa_text("INSERT INTO chat_messages (attendee_id, role, content) VALUES (:aid, 'assistant', :c)"),
            {"aid": aid, "c": response},
        )
        await db.commit()

    return ChatResponse(response=response)


# ── Proactive profile-field drafting ──────────────────────────────────
#
# Three-step flow:
#   1. Frontend calls GET /chat/profile-prompt on chat-open. Backend
#      returns the next field worth offering, or null.
#   2. On Yes, frontend calls POST /chat/draft-field to get 2–3 GPT
#      candidates grounded in the user's existing context.
#   3. On Save, frontend calls POST /chat/save-field. Backend persists,
#      schedules a background re-embed + match refresh, and confirms.
#   On Maybe-later / Cancel, frontend calls POST /chat/decline-prompt
#   so the field is suppressed for DECLINE_COOLDOWN_DAYS.


async def _require_attendee(user: User, db: AsyncSession) -> Attendee:
    if not user.attendee_id:
        raise HTTPException(status_code=404, detail="No attendee profile linked")
    attendee = await db.get(Attendee, user.attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return attendee


@router.get("/profile-prompt", response_model=ProfilePromptResponse)
async def get_profile_prompt(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Return the next missing high-impact profile field worth offering,
    or `field=null` if nothing should be offered right now."""
    attendee = await _require_attendee(user, db)
    field = select_next_field_to_offer(attendee)
    return ProfilePromptResponse(
        field=field,
        current_completeness_pct=compute_completeness_pct(attendee),
        is_sparse=profile_data_quality(attendee) == "SPARSE",
    )


@router.post("/draft-field", response_model=DraftFieldResponse)
@limiter.limit("20/hour")
async def draft_field(
    request: Request,
    data: DraftFieldRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Ask GPT-4o for 2–3 candidate values for a missing field."""
    attendee = await _require_attendee(user, db)
    try:
        candidates, is_sparse = await draft_field_candidates(data.field, attendee)
    except ValueError as e:
        logger.warning("draft_field_candidates failed for %s: %s", attendee.id, e)
        raise HTTPException(
            status_code=502,
            detail="Couldn't draft suggestions right now. Try filling this in from your Profile page.",
        )
    return DraftFieldResponse(candidates=candidates, is_sparse=is_sparse)


@router.post("/save-field")
async def save_field(
    data: SaveFieldRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Persist a user-chosen draft to the attendee row, mark the prompt
    accepted, and schedule a background re-embed + match refresh."""
    value = (data.value or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Looks empty — try a few words.")

    attendee = await _require_attendee(user, db)

    if data.field == "interests":
        # The interests column is an ARRAY(String). Accept either a
        # comma-separated string (most likely from the textarea) or a
        # newline-separated list.
        items = [s.strip() for s in value.replace("\n", ",").split(",")]
        attendee.interests = [s for s in items if s]
    elif data.field == "photo_url":
        if not (value.startswith("http://") or value.startswith("https://")):
            raise HTTPException(
                status_code=400,
                detail="Photo URL must start with http:// or https://",
            )
        attendee.photo_url = value
    else:
        setattr(attendee, data.field, value)

    mark_field_prompt(attendee, data.field, "accepted")
    await db.commit()

    # photo_url doesn't affect embeddings or match quality, so skip the
    # background re-embed — saves an OpenAI call + match-gen round-trip.
    # Dispatch detached (asyncio.create_task, not BackgroundTasks) per
    # profile_pipeline's docstring: BackgroundTasks holds the request worker
    # through the 10-20s pipeline and can 504 the edge.
    if data.field != "photo_url":
        asyncio.create_task(refresh_profile_matches(attendee.id))
    return {"ok": True}


@router.post("/decline-prompt")
async def decline_prompt(
    data: DeclinePromptRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Suppress this field's offer for DECLINE_COOLDOWN_DAYS (30 days)."""
    attendee = await _require_attendee(user, db)
    mark_field_prompt(attendee, data.field, "declined")
    await db.commit()
    return {"ok": True}
