from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_auth
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.concierge import concierge_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/concierge", response_model=ChatResponse)
@limiter.limit("20/hour")
async def chat_concierge(request: Request, data: ChatRequest, db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """AI Concierge — ask about who to meet, meeting prep, and attendee discovery."""
    history = [{"role": m.role, "content": m.content} for m in data.history]
    response = await concierge_chat(
        message=data.message,
        history=history,
        db=db,
    )
    return ChatResponse(response=response)
