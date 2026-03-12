from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import require_auth, require_admin
from app.models.user import User
from app.models.attendee import Attendee, TicketType
from app.schemas.attendee import AttendeeCreate, AttendeeResponse, AttendeeListResponse, OnboardingSubmit, OnboardingResponse

router = APIRouter(prefix="/attendees", tags=["attendees"])


@router.get("/search", response_model=AttendeeListResponse)
async def search_attendees(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Full-text search across name, company, title, goals, and ai_summary."""
    from sqlalchemy import or_, cast, String
    term = f"%{q.lower()}%"
    query = (
        select(Attendee)
        .where(
            or_(
                func.lower(Attendee.name).like(term),
                func.lower(Attendee.company).like(term),
                func.lower(Attendee.title).like(term),
                func.lower(Attendee.goals).like(term),
                func.lower(Attendee.ai_summary).like(term),
            )
        )
        .limit(limit)
    )
    result = await db.execute(query)
    attendees = result.scalars().all()
    return AttendeeListResponse(
        attendees=[AttendeeResponse.model_validate(a) for a in attendees],
        total=len(attendees),
    )


@router.get("/", response_model=AttendeeListResponse)
async def list_attendees(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    ticket_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """List all attendees with pagination and optional filtering."""
    query = select(Attendee)
    if ticket_type:
        query = query.where(Attendee.ticket_type == ticket_type)
    query = query.offset(skip).limit(limit).order_by(Attendee.created_at.desc())

    result = await db.execute(query)
    attendees = result.scalars().all()

    count_query = select(func.count(Attendee.id))
    if ticket_type:
        count_query = count_query.where(Attendee.ticket_type == ticket_type)
    total = (await db.execute(count_query)).scalar()

    return AttendeeListResponse(
        attendees=[AttendeeResponse.model_validate(a) for a in attendees],
        total=total,
    )


@router.get("/{attendee_id}", response_model=AttendeeResponse)
async def get_attendee(attendee_id: UUID, db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """Get attendee profile with enriched data."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return AttendeeResponse.model_validate(attendee)


@router.post("/", response_model=AttendeeResponse, status_code=201)
async def create_attendee(data: AttendeeCreate, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """Register a new attendee."""
    # Check for duplicate email
    existing = await db.execute(select(Attendee).where(Attendee.email == data.email))
    if existing.scalar():
        raise HTTPException(status_code=409, detail="Attendee with this email already exists")

    attendee = Attendee(
        name=data.name,
        email=data.email,
        company=data.company,
        title=data.title,
        ticket_type=TicketType(data.ticket_type),
        interests=data.interests,
        goals=data.goals,
        seeking=data.seeking,
        not_looking_for=data.not_looking_for,
        preferred_geographies=data.preferred_geographies,
        deal_stage=data.deal_stage,
        linkedin_url=data.linkedin_url,
        twitter_handle=data.twitter_handle,
        company_website=data.company_website,
    )
    db.add(attendee)
    await db.commit()
    await db.refresh(attendee)
    return AttendeeResponse.model_validate(attendee)


@router.put("/{attendee_id}", response_model=AttendeeResponse)
async def update_attendee(
    attendee_id: UUID, data: AttendeeCreate, db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Update an attendee's profile."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "ticket_type":
            value = TicketType(value)
        setattr(attendee, field, value)

    # Clear AI fields so they get regenerated
    attendee.ai_summary = None
    attendee.embedding = None
    attendee.intent_tags = []

    await db.commit()
    await db.refresh(attendee)
    return AttendeeResponse.model_validate(attendee)


@router.delete("/{attendee_id}", status_code=204)
async def delete_attendee(attendee_id: UUID, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """Delete an attendee."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    await db.delete(attendee)
    await db.commit()


@router.post("/onboarding", response_model=OnboardingResponse, status_code=200)
async def attendee_onboarding(data: OnboardingSubmit, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint for post-purchase attendee onboarding.

    Attendees authenticate with their Extasy ticket code (printed on their
    confirmation email). This endpoint collects the intent fields that
    Extasy does not provide, enriching the profile for higher-quality matching.
    """
    # Look up attendee by ticket code (case-insensitive)
    result = await db.execute(
        select(Attendee).where(
            func.lower(Attendee.extasy_ticket_code) == data.ticket_code.strip().lower()
        )
    )
    attendee = result.scalar_one_or_none()
    if not attendee:
        raise HTTPException(
            status_code=404,
            detail="Ticket code not found. Check your confirmation email or contact support@proofoftalk.io",
        )

    # Update intent fields (only override if provided)
    if data.title is not None:
        attendee.title = data.title.strip()
    if data.company is not None:
        attendee.company = data.company.strip()
    if data.goals is not None:
        attendee.goals = data.goals.strip()
    if data.interests:
        attendee.interests = data.interests
    if data.seeking:
        attendee.seeking = data.seeking
    if data.deal_stage is not None:
        attendee.deal_stage = data.deal_stage
    if data.linkedin_url is not None:
        attendee.linkedin_url = data.linkedin_url.strip() or None
    if data.twitter_handle is not None:
        handle = data.twitter_handle.strip().lstrip("@")
        attendee.twitter_handle = handle or None
    if data.company_website is not None:
        attendee.company_website = data.company_website.strip() or None

    # Clear stale AI fields so they get regenerated on next enrichment run
    attendee.ai_summary = None
    attendee.embedding = None
    attendee.intent_tags = []

    await db.commit()
    await db.refresh(attendee)

    return OnboardingResponse(
        status="success",
        attendee_id=str(attendee.id),
        name=attendee.name,
        message=(
            "Your profile has been updated. Our AI will generate your personalised match "
            "recommendations before the event. You'll receive them by email."
        ),
    )
