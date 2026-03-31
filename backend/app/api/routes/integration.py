"""
Runa Integration API
====================
Endpoints for Runa/Extasy to integrate the matchmaker into their ticketing platform.
All endpoints require X-API-Key authentication.

See docs/runa-integration-spec.md for full specification.
"""

import secrets
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_api_key
from app.models.attendee import Attendee, Match, TicketType
from app.services.extasy_sync import TICKET_TYPE_MAP, _infer_company, _tier_index

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/integration",
    tags=["integration"],
    dependencies=[Depends(require_api_key)],
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _magic_link_url(token: str) -> str:
    base = settings.APP_PUBLIC_URL.rstrip("/")
    return f"{base}/m/{token}"


def _map_ticket_type(ticket_name: str) -> TicketType:
    key = ticket_name.lower().strip()
    mapped = TICKET_TYPE_MAP.get(key, "delegate")
    return TicketType(mapped)


def _is_profile_complete(attendee: Attendee) -> bool:
    return bool(attendee.goals and attendee.interests)


async def _ensure_magic_token(attendee: Attendee, db: AsyncSession) -> str:
    if not attendee.magic_access_token:
        attendee.magic_access_token = secrets.token_urlsafe(32)
        await db.commit()
    return attendee.magic_access_token


async def _enrich_attendee_background(attendee_id: str) -> None:
    """Run AI enrichment pipeline for a single attendee (background task)."""
    from app.core.database import async_session
    from app.services.enrichment import EnrichmentService
    from app.services.embeddings import generate_ai_summary, embed_attendee, classify_intents, classify_verticals

    try:
        service = EnrichmentService()
        try:
            async with async_session() as db:
                attendee = await db.get(Attendee, attendee_id)
                if not attendee:
                    return
                enriched = await service.enrich_attendee(attendee)
                attendee.enriched_profile = {**(attendee.enriched_profile or {}), **enriched}
                attendee.enriched_at = datetime.utcnow()
                attendee.ai_summary = await generate_ai_summary(attendee)
                attendee.intent_tags = await classify_intents(attendee)
                attendee.vertical_tags = await classify_verticals(attendee)
                attendee.embedding = await embed_attendee(attendee)
                await db.commit()
            logger.info("integration: enrichment complete", attendee_id=attendee_id)
        finally:
            await service.close()
    except Exception as exc:
        logger.error("integration: enrichment failed", attendee_id=attendee_id, error=str(exc))


# ── Schemas ──────────────────────────────────────────────────────────────────

class MagicLinkResponse(BaseModel):
    attendee_id: str
    name: str
    email: str
    magic_link_url: str
    profile_complete: bool
    match_count: int
    created_now: bool


class TicketPurchasedRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    ticket_type: str = "general pass"
    ticket_code: str | None = None
    phone: str | None = None
    country: str | None = None
    city: str | None = None
    paid_amount: str | None = None
    voucher_code: str | None = None
    extasy_order_id: str | None = None
    purchased_at: str | None = None


class TicketPurchasedResponse(BaseModel):
    attendee_id: str
    magic_link_url: str
    status: str  # "created" or "already_exists"
    enrichment_status: str  # "queued" or "complete"


class TicketCancelledRequest(BaseModel):
    email: EmailStr
    extasy_order_id: str | None = None
    reason: str | None = None


class TicketCancelledResponse(BaseModel):
    attendee_id: str
    status: str


class AttendeeStatusResponse(BaseModel):
    attendee_id: str
    name: str
    ticket_type: str
    has_matches: bool
    match_count: int
    mutual_matches: int
    profile_complete: bool
    enriched: bool
    created_at: str


# ── Endpoint A: Magic Link Lookup ────────────────────────────────────────────

@router.get("/magic-link", response_model=MagicLinkResponse)
async def get_magic_link(
    email: str = Query(..., description="Attendee email address"),
    name: str = Query(None, description="Fallback name if attendee needs to be created"),
    ticket_type: str = Query("delegate", description="Ticket type: delegate, sponsor, speaker, vip"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Look up or create an attendee's matchmaker magic link by email."""
    email_lower = email.strip().lower()

    result = await db.execute(select(Attendee).where(Attendee.email == email_lower))
    attendee = result.scalars().first()

    created_now = False

    if not attendee:
        if not name:
            raise HTTPException(
                status_code=404,
                detail="Attendee not found. Provide 'name' parameter to create.",
            )
        # Create on-the-fly
        company, company_website = _infer_company(email_lower)
        attendee = Attendee(
            name=name.strip(),
            email=email_lower,
            company=company,
            title="",
            ticket_type=TicketType(ticket_type) if ticket_type in ("delegate", "sponsor", "speaker", "vip") else TicketType.DELEGATE,
            interests=[],
            magic_access_token=secrets.token_urlsafe(32),
            company_website=company_website or None,
            enriched_profile={"source": "runa_integration", "created_at": datetime.now(timezone.utc).isoformat()},
        )
        db.add(attendee)
        await db.flush()
        await db.commit()
        created_now = True
        background_tasks.add_task(_enrich_attendee_background, str(attendee.id))
        logger.info("integration: created attendee on-the-fly", email=email_lower, attendee_id=str(attendee.id))

    token = await _ensure_magic_token(attendee, db)

    # Count matches
    match_count_result = await db.execute(
        select(func.count(Match.id)).where(
            ((Match.attendee_a_id == attendee.id) | (Match.attendee_b_id == attendee.id))
            & (Match.hidden_by_user.is_(False))
        )
    )
    match_count = match_count_result.scalar() or 0

    return MagicLinkResponse(
        attendee_id=str(attendee.id),
        name=attendee.name,
        email=attendee.email,
        magic_link_url=_magic_link_url(token),
        profile_complete=_is_profile_complete(attendee),
        match_count=match_count,
        created_now=created_now,
    )


# ── Endpoint B: Ticket Purchased Webhook ─────────────────────────────────────

@router.post("/ticket-purchased", response_model=TicketPurchasedResponse, status_code=201)
async def ticket_purchased(
    body: TicketPurchasedRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Receive ticket purchase notification from Runa."""
    email_lower = body.email.strip().lower()
    name = f"{body.first_name.strip()} {body.last_name.strip()}".strip()

    result = await db.execute(select(Attendee).where(Attendee.email == email_lower))
    existing = result.scalars().first()

    if existing:
        token = await _ensure_magic_token(existing, db)
        # Upgrade ticket type if higher tier
        new_type = _map_ticket_type(body.ticket_type)
        if _tier_index(new_type) > _tier_index(existing.ticket_type):
            existing.ticket_type = new_type
            existing.updated_at = datetime.utcnow()
            await db.commit()
        return TicketPurchasedResponse(
            attendee_id=str(existing.id),
            magic_link_url=_magic_link_url(token),
            status="already_exists",
            enrichment_status="complete" if existing.enriched_at else "pending",
        )

    # Create new attendee
    company, company_website = _infer_company(email_lower)
    ticket_type = _map_ticket_type(body.ticket_type)

    enriched_profile = {
        "source": "runa_webhook",
        "extasy_order_id": body.extasy_order_id,
        "ticket_code": body.ticket_code,
        "ticket_name": body.ticket_type,
        "phone": body.phone,
        "city": body.city,
        "country": body.country,
        "paid_amount": body.paid_amount,
        "voucher_code": body.voucher_code,
        "purchased_at": body.purchased_at,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }

    attendee = Attendee(
        name=name,
        email=email_lower,
        company=company,
        title="",
        ticket_type=ticket_type,
        interests=[],
        magic_access_token=secrets.token_urlsafe(32),
        company_website=company_website or None,
        enriched_profile=enriched_profile,
    )
    db.add(attendee)
    await db.flush()
    await db.commit()

    background_tasks.add_task(_enrich_attendee_background, str(attendee.id))
    logger.info("integration: ticket purchased", email=email_lower, attendee_id=str(attendee.id))

    return TicketPurchasedResponse(
        attendee_id=str(attendee.id),
        magic_link_url=_magic_link_url(attendee.magic_access_token),
        status="created",
        enrichment_status="queued",
    )


# ── Endpoint C: Ticket Cancelled ─────────────────────────────────────────────

@router.post("/ticket-cancelled", response_model=TicketCancelledResponse)
async def ticket_cancelled(
    body: TicketCancelledRequest,
    db: AsyncSession = Depends(get_db),
):
    """Receive ticket cancellation/refund notification from Runa."""
    email_lower = body.email.strip().lower()

    result = await db.execute(select(Attendee).where(Attendee.email == email_lower))
    attendee = result.scalars().first()

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    # Store cancellation info in enriched_profile
    profile = attendee.enriched_profile or {}
    profile["cancelled"] = True
    profile["cancel_reason"] = body.reason
    profile["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    attendee.enriched_profile = profile
    attendee.updated_at = datetime.utcnow()
    await db.commit()

    logger.info("integration: ticket cancelled", email=email_lower, reason=body.reason)

    return TicketCancelledResponse(
        attendee_id=str(attendee.id),
        status="deactivated",
    )


# ── Endpoint D: Attendee Status ──────────────────────────────────────────────

@router.get("/attendee-status", response_model=AttendeeStatusResponse)
async def attendee_status(
    email: str = Query(..., description="Attendee email address"),
    db: AsyncSession = Depends(get_db),
):
    """Check an attendee's matchmaker status."""
    email_lower = email.strip().lower()

    result = await db.execute(select(Attendee).where(Attendee.email == email_lower))
    attendee = result.scalars().first()

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    # Count total matches
    match_count_result = await db.execute(
        select(func.count(Match.id)).where(
            ((Match.attendee_a_id == attendee.id) | (Match.attendee_b_id == attendee.id))
            & (Match.hidden_by_user.is_(False))
        )
    )
    match_count = match_count_result.scalar() or 0

    # Count mutual matches (both accepted)
    mutual_result = await db.execute(
        select(func.count(Match.id)).where(
            ((Match.attendee_a_id == attendee.id) | (Match.attendee_b_id == attendee.id))
            & (Match.status_a == "accepted")
            & (Match.status_b == "accepted")
        )
    )
    mutual_count = mutual_result.scalar() or 0

    return AttendeeStatusResponse(
        attendee_id=str(attendee.id),
        name=attendee.name,
        ticket_type=attendee.ticket_type.value if hasattr(attendee.ticket_type, 'value') else str(attendee.ticket_type),
        has_matches=match_count > 0,
        match_count=match_count,
        mutual_matches=mutual_count,
        profile_complete=_is_profile_complete(attendee),
        enriched=attendee.enriched_at is not None,
        created_at=attendee.created_at.isoformat() if attendee.created_at else "",
    )
