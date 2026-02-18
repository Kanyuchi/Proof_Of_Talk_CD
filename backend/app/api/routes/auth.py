import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, async_session
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import require_auth
from app.models.user import User
from app.models.attendee import Attendee
from app.schemas.auth import RegisterRequest, LoginRequest, Token, UserResponse
from app.services.matching import MatchingEngine

router = APIRouter(prefix="/auth", tags=["auth"])


async def _process_attendee_bg(attendee_id: uuid.UUID) -> None:
    """Background task: run AI pipeline on a newly registered attendee."""
    async with async_session() as db:
        engine = MatchingEngine(db)
        attendee = await db.get(Attendee, attendee_id)
        if attendee:
            await engine.process_attendee(attendee)


@router.post("/register", response_model=Token, status_code=201)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user + attendee profile. Returns a JWT token."""
    # Uniqueness checks
    if (await db.execute(select(User).where(User.email == data.email))).scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if (await db.execute(select(Attendee).where(Attendee.email == data.email))).scalars().first():
        raise HTTPException(status_code=400, detail="Email already in use")

    # Create attendee profile first
    attendee = Attendee(
        name=data.name,
        email=data.email,
        company=data.company,
        title=data.title,
        ticket_type=data.ticket_type,
        interests=data.interests,
        goals=data.goals,
        linkedin_url=data.linkedin_url,
        twitter_handle=data.twitter_handle,
        company_website=data.company_website,
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

    # Kick off AI processing in the background (non-blocking)
    background_tasks.add_task(_process_attendee_bg, attendee.id)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
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
