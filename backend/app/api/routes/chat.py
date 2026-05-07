from fastapi import APIRouter, Depends, Request
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_auth
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.concierge import concierge_chat

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
