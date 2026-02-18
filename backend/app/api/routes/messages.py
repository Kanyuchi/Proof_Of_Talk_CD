from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import require_auth
from app.models.user import User
from app.models.attendee import Attendee, Match
from app.models.message import Conversation, Message

router = APIRouter(prefix="/messages", tags=["messages"])


async def _get_attendee(user: User, db: AsyncSession) -> Attendee:
    if not user.attendee_id:
        raise HTTPException(status_code=403, detail="No attendee profile linked to account")
    attendee = await db.get(Attendee, user.attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee profile not found")
    return attendee


async def _get_and_verify_match(match_id: UUID, attendee: Attendee, db: AsyncSession) -> Match:
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if attendee.id not in (match.attendee_a_id, match.attendee_b_id):
        raise HTTPException(status_code=403, detail="Access denied — not your match")
    return match


async def _get_or_create_conversation(match_id: UUID, db: AsyncSession) -> Conversation:
    conv = (await db.execute(
        select(Conversation).where(Conversation.match_id == match_id)
    )).scalars().first()
    if not conv:
        conv = Conversation(match_id=match_id)
        db.add(conv)
        await db.flush()
    return conv


@router.get("/conversations")
async def list_conversations(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations (accepted matches) for the current user."""
    attendee = await _get_attendee(user, db)

    accepted = (await db.execute(
        select(Match).where(
            ((Match.attendee_a_id == attendee.id) | (Match.attendee_b_id == attendee.id))
        )
    )).scalars().all()

    summaries = []
    for match in accepted:
        other_id = match.attendee_b_id if match.attendee_a_id == attendee.id else match.attendee_a_id
        other = await db.get(Attendee, other_id)

        conv = (await db.execute(
            select(Conversation).where(Conversation.match_id == match.id)
        )).scalars().first()

        last_msg_content = None
        last_msg_at = None
        unread = 0

        if conv:
            last = (await db.execute(
                select(Message).where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc()).limit(1)
            )).scalars().first()
            if last:
                last_msg_content = last.content
                last_msg_at = last.created_at.isoformat()

            unread_msgs = (await db.execute(
                select(Message).where(
                    (Message.conversation_id == conv.id)
                    & (Message.sender_attendee_id != attendee.id)
                    & (Message.read_at.is_(None))
                )
            )).scalars().all()
            unread = len(unread_msgs)

        summaries.append({
            "match_id": str(match.id),
            "match_status": match.status,
            "conversation_id": str(conv.id) if conv else None,
            "other_attendee_id": str(other.id) if other else None,
            "other_attendee_name": other.name if other else "Unknown",
            "other_attendee_company": other.company if other else "",
            "other_attendee_title": other.title if other else "",
            "other_attendee_ticket": other.ticket_type if other else "delegate",
            "last_message": last_msg_content,
            "last_message_at": last_msg_at,
            "unread_count": unread,
        })

    return {"conversations": summaries}


@router.get("/conversations/{match_id}")
async def get_conversation(
    match_id: UUID,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get or create a conversation for a match and return all messages."""
    attendee = await _get_attendee(user, db)
    match = await _get_and_verify_match(match_id, attendee, db)
    conv = await _get_or_create_conversation(match.id, db)

    msgs = (await db.execute(
        select(Message).where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )).scalars().all()

    # Mark unread messages from other party as read
    for msg in msgs:
        if msg.sender_attendee_id != attendee.id and msg.read_at is None:
            msg.read_at = datetime.utcnow()
    await db.commit()

    # Build message list with sender info
    other_id = match.attendee_b_id if match.attendee_a_id == attendee.id else match.attendee_a_id
    other = await db.get(Attendee, other_id)

    message_list = []
    for msg in msgs:
        is_mine = msg.sender_attendee_id == attendee.id
        sender_name = attendee.name if is_mine else (other.name if other else "Unknown")
        message_list.append({
            "id": str(msg.id),
            "conversation_id": str(msg.conversation_id),
            "sender_attendee_id": str(msg.sender_attendee_id),
            "sender_name": sender_name,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "is_mine": is_mine,
        })

    return {
        "conversation_id": str(conv.id),
        "match_id": str(match.id),
        "match_status": match.status,
        "other_attendee": {
            "id": str(other.id),
            "name": other.name,
            "company": other.company,
            "title": other.title,
            "ticket_type": other.ticket_type,
        } if other else None,
        "messages": message_list,
    }


@router.post("/conversations/{match_id}")
async def send_message(
    match_id: UUID,
    data: dict,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a match conversation."""
    content = (data.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    attendee = await _get_attendee(user, db)
    await _get_and_verify_match(match_id, attendee, db)
    conv = await _get_or_create_conversation(match_id, db)

    msg = Message(
        conversation_id=conv.id,
        sender_attendee_id=attendee.id,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_attendee_id": str(msg.sender_attendee_id),
        "sender_name": attendee.name,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
        "read_at": None,
        "is_mine": True,
    }


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Total count of unread messages for the current user."""
    attendee = await _get_attendee(user, db)

    matches = (await db.execute(
        select(Match.id).where(
            (Match.attendee_a_id == attendee.id) | (Match.attendee_b_id == attendee.id)
        )
    )).scalars().all()

    if not matches:
        return {"unread_count": 0}

    convs = (await db.execute(
        select(Conversation.id).where(Conversation.match_id.in_(matches))
    )).scalars().all()

    if not convs:
        return {"unread_count": 0}

    unread = (await db.execute(
        select(Message).where(
            (Message.conversation_id.in_(convs))
            & (Message.sender_attendee_id != attendee.id)
            & (Message.read_at.is_(None))
        )
    )).scalars().all()

    return {"unread_count": len(unread)}
