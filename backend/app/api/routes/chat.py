from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.concierge import concierge_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/concierge", response_model=ChatResponse)
async def chat_concierge(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI Concierge — ask about who to meet, meeting prep, and attendee discovery."""
    history = [{"role": m.role, "content": m.content} for m in data.history]
    response = await concierge_chat(
        message=data.message,
        history=history,
        db=db,
    )
    return ChatResponse(response=response)
