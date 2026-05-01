import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_, and_, func
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
    redact_for_privacy,
)
from app.services.matching import MatchingEngine
from app.services.slots import mutual_free_slots, has_conflict
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
            is_mutual = match.status_a == "accepted" and match.status_b == "accepted"
            att_dict = AttendeeResponse.model_validate(matched).model_dump()
            resp.matched_attendee = AttendeeResponse(**redact_for_privacy(att_dict, is_mutual_match=is_mutual))
            if is_mutual and not match.meeting_time:
                resp.mutual_free_slots = await mutual_free_slots(db, attendee_id, other_id)
        match_responses.append(resp)

    return MatchListResponse(matches=match_responses, attendee_id=attendee_id)


@router.get("/m/{token}", response_model=MatchListResponse)
async def get_matches_by_magic_link(
    token: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get matches via magic link — no login required."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")

    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token == token)
    )
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    match_result = await db.execute(
        select(Match)
        .where(
            or_(
                Match.attendee_a_id == attendee.id,
                Match.attendee_b_id == attendee.id,
            )
            & (Match.hidden_by_user.is_(False))
        )
        .order_by(Match.overall_score.desc())
        .limit(limit)
    )
    matches = match_result.scalars().all()

    match_responses = []
    for match in matches:
        other_id = (
            match.attendee_b_id
            if match.attendee_a_id == attendee.id
            else match.attendee_a_id
        )
        matched = await db.get(Attendee, other_id)
        resp = MatchResponse.model_validate(match)
        if matched:
            is_mutual = match.status_a == "accepted" and match.status_b == "accepted"
            att_dict = AttendeeResponse.model_validate(matched).model_dump()
            resp.matched_attendee = AttendeeResponse(**redact_for_privacy(att_dict, is_mutual_match=is_mutual))
            if is_mutual and not match.meeting_time:
                resp.mutual_free_slots = await mutual_free_slots(db, attendee.id, other_id)
        match_responses.append(resp)

    return MatchListResponse(matches=match_responses, attendee_id=attendee.id)


class MagicProfileUpdate(BaseModel):
    """Lightweight profile update via magic token (no JWT required)."""
    twitter_handle: str | None = None
    target_companies: str | None = None
    photo_url: str | None = None
    privacy_mode: str | None = None


@router.patch("/m/{token}/profile")
async def update_profile_via_magic_link(
    token: str,
    data: MagicProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update attendee profile fields via magic link — no login required."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")

    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token == token)
    )
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    if data.twitter_handle is not None:
        attendee.twitter_handle = data.twitter_handle
    if data.target_companies is not None:
        attendee.target_companies = data.target_companies
    if data.photo_url is not None:
        attendee.photo_url = data.photo_url
    if data.privacy_mode is not None and data.privacy_mode in ("full", "b2b_only"):
        attendee.privacy_mode = data.privacy_mode

    await db.commit()
    return {"status": "updated"}


@router.get("/pending-count")
async def get_pending_match_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Count matches where the other party accepted but the current user hasn't responded yet."""
    if not user.attendee_id:
        return {"pending_count": 0}

    aid = user.attendee_id
    result = await db.execute(
        select(func.count(Match.id)).where(
            or_(
                # I'm attendee_a, other accepted, I haven't responded
                and_(Match.attendee_a_id == aid, Match.status_a == "pending", Match.status_b == "accepted"),
                # I'm attendee_b, other accepted, I haven't responded
                and_(Match.attendee_b_id == aid, Match.status_b == "pending", Match.status_a == "accepted"),
            )
        )
    )
    count = result.scalar() or 0
    return {"pending_count": count}


@router.post("/generate-tokens", status_code=200)
async def generate_magic_tokens(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Generate magic_access_tokens for all attendees that don't have one yet."""
    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token.is_(None))
    )
    attendees = result.scalars().all()
    count = 0
    for att in attendees:
        att.magic_access_token = secrets.token_urlsafe(32)
        count += 1
    await db.commit()
    return {"status": "completed", "tokens_generated": count}


@router.post("/generate/{attendee_id}")
async def generate_matches_for_attendee(
    attendee_id: UUID,
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Generate match recommendations for a single attendee."""
    import logging
    logger = logging.getLogger(__name__)
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
    except Exception as e:
        logger.error("Match generation failed for %s: %s", attendee_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Match generation error: {type(e).__name__}: {str(e)[:200]}")


@router.post("/generate-all")
async def generate_all_matches(
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Trigger match generation for all attendees."""
    import logging
    logger = logging.getLogger(__name__)
    engine = MatchingEngine(db)
    try:
        total = await engine.generate_all_matches(top_k)
        return {"status": "completed", "total_matches": total}
    except Exception as e:
        logger.error("generate-all failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Match generation error: {type(e).__name__}: {str(e)[:200]}")


@router.post("/process-all")
async def process_all_attendees(db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """Process all attendees: generate AI summaries, intents, and embeddings."""
    import logging
    logger = logging.getLogger(__name__)
    engine = MatchingEngine(db)
    try:
        count = await engine.process_all_attendees()
        return {"status": "completed", "attendees_processed": count}
    except Exception as e:
        logger.error("process-all failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {type(e).__name__}: {str(e)[:200]}")


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
    prev_status = match.status
    match.status = _compute_overall_status(match.status_a, match.status_b)

    if data.status == "declined":
        match.decline_reason = data.decline_reason

    await db.commit()
    await db.refresh(match)

    # Fire-and-forget: notify both parties when a mutual match is newly confirmed
    if match.status == "accepted" and prev_status != "accepted":
        try:
            from app.services.email import send_mutual_match_email
            attendee_a = await db.get(Attendee, match.attendee_a_id)
            attendee_b = await db.get(Attendee, match.attendee_b_id)
            if attendee_a and attendee_b:
                for recipient, partner in [(attendee_a, attendee_b), (attendee_b, attendee_a)]:
                    if recipient.email:
                        send_mutual_match_email(
                            to_email=recipient.email,
                            attendee_name=recipient.name,
                            other_name=partner.name,
                            other_title=partner.title or "",
                            other_company=partner.company or "",
                        )
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("Mutual match email failed: %s", exc)

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

    # Reject if either party already has a meeting at that time. Use a different
    # status code (409 Conflict) so the frontend can distinguish from validation
    # errors and show a "slot just got taken" message.
    for other_id in (match.attendee_a_id, match.attendee_b_id):
        if await has_conflict(db, other_id, data.meeting_time):
            # Skip if the conflict is *this* match (idempotent re-save)
            if match.meeting_time == data.meeting_time:
                continue
            raise HTTPException(
                status_code=409,
                detail="That slot is no longer free for both of you — pick another time",
            )

    match.meeting_time = data.meeting_time
    match.meeting_location = data.meeting_location or "Louvre Palace, Paris — TBD at venue"

    await db.commit()
    await db.refresh(match)

    # Fire-and-forget: send meeting confirmation to both parties
    try:
        from datetime import timezone
        from app.services.email import send_meeting_confirmation_email
        attendee_a = await db.get(Attendee, match.attendee_a_id)
        attendee_b = await db.get(Attendee, match.attendee_b_id)
        if attendee_a and attendee_b and match.meeting_time:
            # Format the time for the email (simple ISO → readable)
            dt = match.meeting_time
            if hasattr(dt, "strftime"):
                time_str = dt.strftime("%a %b %-d · %H:%M") + " (Louvre time)"
            else:
                time_str = str(match.meeting_time)
            location = match.meeting_location or "Louvre Palace, Paris"
            for recipient, partner in [(attendee_a, attendee_b), (attendee_b, attendee_a)]:
                if recipient.email:
                    send_meeting_confirmation_email(
                        to_email=recipient.email,
                        attendee_name=recipient.name,
                        other_name=partner.name,
                        other_company=partner.company or "",
                        meeting_time_str=time_str,
                        meeting_location=location,
                    )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("Meeting confirmation email failed: %s", exc)

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
