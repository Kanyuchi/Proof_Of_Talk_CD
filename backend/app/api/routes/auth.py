import asyncio
import logging
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, async_session
from app.core.security import verify_password, get_password_hash, create_access_token, create_reset_token, decode_reset_token
from app.core.deps import require_auth
from app.core.limiter import limiter
from app.models.user import User
from app.models.attendee import Attendee
from app.schemas.auth import RegisterRequest, LoginRequest, Token, UserResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.services.matching import MatchingEngine
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _process_attendee_bg(attendee_id: uuid.UUID) -> None:
    """Run AI pipeline on a newly registered attendee.

    Fire-and-forget — invoked via `asyncio.create_task`, NOT FastAPI's
    BackgroundTasks. Reason: BackgroundTasks holds the request worker
    until the task completes, so a 10-20s OpenAI/Grid/embed pipeline
    can cause the Netlify edge to 504 even though the response is ready.
    asyncio.create_task lets the worker return immediately and the AI
    processing runs detached on the event loop.
    """
    try:
        async with async_session() as db:
            engine = MatchingEngine(db)
            attendee = await db.get(Attendee, attendee_id)
            if attendee:
                await engine.process_attendee(attendee)
    except Exception as exc:
        logger.exception("Detached attendee processing failed for %s: %s", attendee_id, exc)


@router.post("/register", response_model=Token, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user + attendee profile. Returns a JWT token."""
    # Uniqueness check — only block if a USER (with login) already exists
    # at this email. An attendee row at this email is fine: it means the
    # person bought a Rhuna/Extasy ticket (cron-created) or was added by
    # ops via the speaker sheet, and is now claiming the account. We
    # link the new user to that existing attendee row and merge any
    # fields they supplied that the row was missing.
    if (await db.execute(select(User).where(User.email == data.email))).scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_attendee = (await db.execute(
        select(Attendee).where(Attendee.email == data.email)
    )).scalars().first()

    if existing_attendee:
        # Merge non-empty registration fields onto the existing row —
        # the user is the source of truth for their own profile.
        for field in ("name", "company", "title", "linkedin_url",
                      "twitter_handle", "company_website", "goals",
                      "deal_stage"):
            val = getattr(data, field, None)
            if val:
                setattr(existing_attendee, field, val)
        for list_field in ("interests", "seeking", "not_looking_for",
                           "preferred_geographies"):
            val = getattr(data, list_field, None)
            if val:
                setattr(existing_attendee, list_field, val)
        if data.privacy_mode in ("full", "b2b_only"):
            existing_attendee.privacy_mode = data.privacy_mode
        if not existing_attendee.magic_access_token:
            existing_attendee.magic_access_token = secrets.token_urlsafe(32)
        attendee = existing_attendee
    else:
        # Fresh registration — create a new attendee row.
        attendee = Attendee(
            name=data.name,
            email=data.email,
            company=data.company,
            title=data.title,
            ticket_type=data.ticket_type,
            interests=data.interests,
            goals=data.goals,
            seeking=data.seeking,
            not_looking_for=data.not_looking_for,
            preferred_geographies=data.preferred_geographies,
            deal_stage=data.deal_stage,
            linkedin_url=data.linkedin_url,
            twitter_handle=data.twitter_handle,
            company_website=data.company_website,
            magic_access_token=secrets.token_urlsafe(32),
            privacy_mode=data.privacy_mode if data.privacy_mode in ("full", "b2b_only") else "full",
        )
        db.add(attendee)

    await db.flush()  # ensures attendee.id is populated

    # Create auth user
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.name,
        attendee_id=attendee.id,
    )
    db.add(user)
    await db.commit()

    # Fire-and-forget AI processing. asyncio.create_task lets the worker
    # release the response immediately; FastAPI's BackgroundTasks would
    # hold the worker until processing finishes, causing edge timeouts
    # on slow OpenAI/Grid pipelines (William Raulin's 504, 2026-05-15).
    asyncio.create_task(_process_attendee_bg(attendee.id))

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password, returns JWT token."""
    user = (await db.execute(select(User).where(User.email == data.email))).scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    """Get the currently authenticated user."""
    return user


@router.put("/profile")
async def update_profile(
    data: dict,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's attendee profile."""
    if not user.attendee_id:
        raise HTTPException(status_code=404, detail="No attendee profile linked")

    attendee = await db.get(Attendee, user.attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee profile not found")

    allowed = {
        "name", "company", "title", "goals", "interests",
        "seeking", "not_looking_for", "preferred_geographies", "deal_stage",
        "linkedin_url", "twitter_handle", "company_website", "photo_url",
        "privacy_mode",
    }
    for field, value in data.items():
        if field in allowed:
            if field == "privacy_mode" and value not in ("full", "b2b_only"):
                continue
            setattr(attendee, field, value)

    # Update display name on User too if name changed
    if "name" in data:
        user.full_name = data["name"]

    # Clear embedding so it regenerates on next enrichment run
    attendee.embedding = None

    await db.commit()
    await db.refresh(attendee)

    from app.schemas.attendee import AttendeeResponse
    return {
        "user": UserResponse.model_validate(user),
        "attendee": AttendeeResponse.model_validate(attendee),
    }


@router.get("/my-magic-link")
async def get_my_magic_link(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's magic link token for QR code generation."""
    if not user.attendee_id:
        raise HTTPException(status_code=404, detail="No attendee profile linked")
    attendee = await db.get(Attendee, user.attendee_id)
    if not attendee or not attendee.magic_access_token:
        raise HTTPException(status_code=404, detail="No magic link available")
    return {"magic_token": attendee.magic_access_token}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password reset email if the account exists. Always returns success to prevent email enumeration."""
    user = (await db.execute(select(User).where(User.email == data.email))).scalars().first()
    if user:
        token = create_reset_token(str(user.id))
        send_password_reset_email(to_email=user.email, user_name=user.full_name, reset_token=token)
        logger.info("Password reset email sent to %s", data.email)
    else:
        logger.info("Password reset requested for non-existent email %s", data.email)
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid reset token."""
    user_id = decode_reset_token(data.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired")

    user = (await db.execute(select(User).where(User.id == uuid.UUID(user_id)))).scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired")

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}
