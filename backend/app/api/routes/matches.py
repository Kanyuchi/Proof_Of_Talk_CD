from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.attendee import Attendee, Match
from app.schemas.attendee import (
    MatchResponse,
    MatchListResponse,
    MatchStatusUpdate,
    ScheduleMeetingRequest,
    MatchFeedbackUpdate,
    AttendeeResponse,
)
from app.services.matching import MatchingEngine
from app.core.deps import require_auth, require_admin
from app.models.user import User

router = APIRouter(prefix="/matches", tags=["matches"])


def _compute_overall_status(status_a: str, status_b: str) -> str:
    """Compute overall match state from per-party statuses."""
    if "declined" in (status_a, status_b):
        return "declined"
    if status_a == "met" and status_b == "met":
        return "met"
    # accepted+met still counts as accepted until both mark met
    if status_a in {"accepted", "met"} and status_b in {"accepted", "met"}:
        return "accepted"
    return "pending"


@router.get("/{attendee_id}", response_model=MatchListResponse)
async def get_matches(
    attendee_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Get AI-generated match recommendations for an attendee."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    result = await db.execute(
        select(Match)
        .where(
            or_(
                Match.attendee_a_id == attendee_id,
                Match.attendee_b_id == attendee_id,
            )
            & (Match.hidden_by_user.is_(False))
        )
        .order_by(Match.overall_score.desc())
        .limit(limit)
    )
    matches = result.scalars().all()

    match_responses = []
    for match in matches:
        # Always return the OTHER party's profile, regardless of a/b position
        other_id = (
            match.attendee_b_id
            if match.attendee_a_id == attendee_id
            else match.attendee_a_id
        )
        matched = await db.get(Attendee, other_id)
        resp = MatchResponse.model_validate(match)
        if matched:
            resp.matched_attendee = AttendeeResponse.model_validate(matched)
        match_responses.append(resp)

    return MatchListResponse(matches=match_responses, attendee_id=attendee_id)


@router.post("/generate/{attendee_id}")
async def generate_matches_for_attendee(
    attendee_id: UUID,
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Generate match recommendations for a single attendee."""
    engine = MatchingEngine(db)
    try:
        matches = await engine.generate_matches_for_attendee(attendee_id, top_k)
        return {
            "status": "completed",
            "attendee_id": str(attendee_id),
            "matches_generated": len(matches),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/generate-all")
async def generate_all_matches(
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Trigger match generation for all attendees."""
    engine = MatchingEngine(db)
    total = await engine.generate_all_matches(top_k)
    return {"status": "completed", "total_matches": total}


@router.post("/process-all")
async def process_all_attendees(db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """Process all attendees: generate AI summaries, intents, and embeddings."""
    engine = MatchingEngine(db)
    count = await engine.process_all_attendees()
    return {"status": "completed", "attendees_processed": count}


@router.patch("/{match_id}/status", response_model=MatchResponse)
async def update_match_status(
    match_id: UUID,
    data: MatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Accept or decline a match — records per-party status and computes mutual state."""
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if data.status not in ("accepted", "declined", "met"):
        raise HTTPException(status_code=400, detail="Status must be accepted, declined, or met")

    # Determine which side this user is on, based on their linked attendee_id
    if user.attendee_id and str(user.attendee_id) == str(match.attendee_a_id):
        match.status_a = data.status
    elif user.attendee_id and str(user.attendee_id) == str(match.attendee_b_id):
        match.status_b = data.status
    else:
        # Admin or unlinked user — update the legacy status field directly
        match.status = data.status
        await db.commit()
        await db.refresh(match)
        return MatchResponse.model_validate(match)

    # Recompute overall status from both sides
    match.status = _compute_overall_status(match.status_a, match.status_b)

    if data.status == "declined":
        match.decline_reason = data.decline_reason

    await db.commit()
    await db.refresh(match)
    return MatchResponse.model_validate(match)


@router.patch("/{match_id}/schedule", response_model=MatchResponse)
async def schedule_meeting(
    match_id: UUID,
    data: ScheduleMeetingRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Propose a meeting time for a mutually accepted match."""
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail="Meeting time can only be set on mutually accepted matches",
        )

    match.meeting_time = data.meeting_time
    match.meeting_location = data.meeting_location or "Louvre Palace, Paris — TBD at venue"

    await db.commit()
    await db.refresh(match)
    return MatchResponse.model_validate(match)


@router.patch("/{match_id}/feedback", response_model=MatchResponse)
async def update_meeting_feedback(
    match_id: UUID,
    data: MatchFeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Save post-meeting outcome and satisfaction feedback."""
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if data.meeting_outcome is not None:
        match.meeting_outcome = data.meeting_outcome
    if data.satisfaction_score is not None:
        # Keep satisfaction in a 1-5 range for dashboard averages
        score = max(1.0, min(5.0, float(data.satisfaction_score)))
        match.satisfaction_score = score
    if data.met_at is not None:
        match.met_at = data.met_at
    elif data.meeting_outcome and not match.met_at:
        from datetime import datetime, timezone
        match.met_at = datetime.now(timezone.utc)
    if data.hidden_by_user is not None:
        match.hidden_by_user = data.hidden_by_user

    await db.commit()
    await db.refresh(match)
    return MatchResponse.model_validate(match)
