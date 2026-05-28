import asyncio
import logging
import secrets
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
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
from app.services.avatars import upload_avatar, AvatarError, MAX_BYTES
from app.services.matching import MatchingEngine
from app.services.profile_pipeline import refresh_profile_matches
from app.services.slots import mutual_free_slots, has_conflict
from app.services.match_visibility import ViewerMatch, order_and_cap, tier_limit, next_tier_unlock
from app.services.concierge import profile_data_quality, compute_completeness_pct
from app.core.deps import require_auth, require_admin
from app.core.limiter import limiter
from app.models.user import User

logger = logging.getLogger(__name__)

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


def _to_viewer_match(match: Match, viewer_id: UUID) -> ViewerMatch:
    """Orient a Match row from `viewer_id`'s perspective for ordering/cap."""
    i_am_a = match.attendee_a_id == viewer_id
    return ViewerMatch(
        match=match,
        viewer_status=match.status_a if i_am_a else match.status_b,
        other_status=match.status_b if i_am_a else match.status_a,
        viewer_deferred_at=match.deferred_a_at if i_am_a else match.deferred_b_at,
        overall_score=match.overall_score or 0.0,
    )


async def _build_match_response(db: AsyncSession, match: Match, viewer_id: UUID) -> MatchResponse:
    """Build a privacy-redacted MatchResponse for the OTHER party, with free slots."""
    other_id = (
        match.attendee_b_id if match.attendee_a_id == viewer_id else match.attendee_a_id
    )
    matched = await db.get(Attendee, other_id)
    resp = MatchResponse.model_validate(match)
    if matched:
        is_mutual = match.status_a == "accepted" and match.status_b == "accepted"
        att_dict = AttendeeResponse.model_validate(matched).model_dump()
        resp.matched_attendee = AttendeeResponse(
            **redact_for_privacy(att_dict, is_mutual_match=is_mutual)
        )
        if is_mutual and not match.meeting_time:
            resp.mutual_free_slots = await mutual_free_slots(db, viewer_id, other_id)
    return resp


# IMPORTANT: static routes MUST be declared before the parameterized
# "/{attendee_id}" catch-all below. Starlette matches in declaration order, so
# a static path placed after it (e.g. "/pending-count") gets captured as an
# attendee_id and 422s on UUID validation. Keep all literal GET paths up here.
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


@router.get("/{attendee_id}", response_model=MatchListResponse)
async def get_matches(
    attendee_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get match recommendations, capped by the viewer's completeness tier.

    Admins bypass the cap and see the full pool (with tier labels) for any
    attendee. Regular viewers get a tier-limited review window plus all
    incoming requests and committed matches.
    """
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    result = await db.execute(
        select(Match).where(
            or_(Match.attendee_a_id == attendee_id, Match.attendee_b_id == attendee_id)
            & (Match.hidden_by_user.is_(False))
        )
    )
    rows = list(result.scalars().all())

    tier = profile_data_quality(attendee)
    pct = compute_completeness_pct(attendee)

    # Admins: full pool, score-ordered, no cap.
    if getattr(user, "is_admin", False):
        rows.sort(key=lambda m: m.overall_score or 0.0, reverse=True)
        responses = [await _build_match_response(db, m, attendee_id) for m in rows[:limit]]
        return MatchListResponse(
            matches=responses, attendee_id=attendee_id, tier=tier,
            viewer=AttendeeResponse.model_validate(attendee),
            visible_count=len(responses), locked_count=0,
            next_tier_at=None, completeness_pct=pct,
        )

    vms = [_to_viewer_match(m, attendee_id) for m in rows]
    visible, locked = order_and_cap(vms, tier_limit(tier))
    responses = [await _build_match_response(db, vm.match, attendee_id) for vm in visible]
    return MatchListResponse(
        matches=responses, attendee_id=attendee_id, tier=tier,
        viewer=AttendeeResponse.model_validate(attendee),
        visible_count=len(responses), locked_count=locked,
        next_tier_at=next_tier_unlock(tier), completeness_pct=pct,
    )


@router.get("/m/{token}", response_model=MatchListResponse)
async def get_matches_by_magic_link(
    token: str,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get matches via magic link — no login required. Cap applies (the
    token's own attendee is the viewer)."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")

    result = await db.execute(select(Attendee).where(Attendee.magic_access_token == token))
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    # Adoption tracking — stamp last_seen_at (the magic-link majority path),
    # throttled to once/hour and best-effort so it never breaks the match view.
    try:
        from datetime import timedelta
        now = datetime.utcnow()
        if attendee.last_seen_at is None or (now - attendee.last_seen_at) > timedelta(hours=1):
            attendee.last_seen_at = now
            await db.commit()
    except Exception as exc:
        logger.warning("magic-link last_seen_at write failed: %s", exc)  # best-effort; response takes priority

    match_result = await db.execute(
        select(Match).where(
            or_(Match.attendee_a_id == attendee.id, Match.attendee_b_id == attendee.id)
            & (Match.hidden_by_user.is_(False))
        )
    )
    rows = list(match_result.scalars().all())

    tier = profile_data_quality(attendee)
    pct = compute_completeness_pct(attendee)
    vms = [_to_viewer_match(m, attendee.id) for m in rows]
    visible, locked = order_and_cap(vms, tier_limit(tier))
    responses = [await _build_match_response(db, vm.match, attendee.id) for vm in visible]

    # Drives the MagicMatches "Set your password" panel: default-expanded for
    # unclaimed visitors, collapsed for those who already have a User row.
    user_row = await db.execute(
        select(User.id).where(User.attendee_id == attendee.id).limit(1)
    )
    has_account = user_row.scalars().first() is not None

    return MatchListResponse(
        matches=responses, attendee_id=attendee.id, tier=tier,
        viewer=AttendeeResponse.model_validate(attendee),
        visible_count=len(responses), locked_count=locked,
        next_tier_at=next_tier_unlock(tier), completeness_pct=pct,
        has_account=has_account,
    )


@router.get("/m/{token}/incoming-summary")
async def magic_link_incoming_summary(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counts for the Phase 2 reciprocity banner on MagicMatches.

    Returns counts across the FULL match set (not the capped/visible window
    GET /m/{token} returns), so the banner stays honest even when the matches
    driving it sit below the tier cap.
    """
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")

    result = await db.execute(select(Attendee).where(Attendee.magic_access_token == token))
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    match_result = await db.execute(
        select(Match).where(
            or_(Match.attendee_a_id == attendee.id, Match.attendee_b_id == attendee.id)
            & (Match.hidden_by_user.is_(False))
        )
    )
    rows = list(match_result.scalars().all())

    pending_for_you = 0
    accepted_back = 0
    for m in rows:
        if m.attendee_a_id == attendee.id:
            my_status, other_status = m.status_a, m.status_b
        else:
            my_status, other_status = m.status_b, m.status_a
        if other_status == "accepted" and my_status == "pending":
            pending_for_you += 1
        if my_status == "accepted" and other_status == "accepted":
            accepted_back += 1

    return {
        "count_pending_for_you": pending_for_you,
        "count_accepted_back": accepted_back,
    }


class MagicDeferRequest(BaseModel):
    match_id: UUID


class MagicStatusRequest(BaseModel):
    match_id: UUID
    status: str
    decline_reason: str | None = None


@router.patch("/{match_id}/defer", response_model=MatchResponse)
async def defer_match(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Soft-defer ("Maybe later") — stamps the viewer's side; the card leaves
    the visible window and resurfaces at the back once fresh ones run out."""
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    now = datetime.utcnow()
    if user.attendee_id and str(user.attendee_id) == str(match.attendee_a_id):
        match.deferred_a_at = now
    elif user.attendee_id and str(user.attendee_id) == str(match.attendee_b_id):
        match.deferred_b_at = now
    else:
        raise HTTPException(status_code=403, detail="Not your match")
    await db.commit()
    await db.refresh(match)
    return await _build_match_response(db, match, user.attendee_id)


@router.patch("/m/{token}/defer", response_model=MatchResponse)
async def defer_match_by_magic_link(
    token: str,
    data: MagicDeferRequest,
    db: AsyncSession = Depends(get_db),
):
    """Magic-link soft-defer — no login required."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")
    result = await db.execute(select(Attendee).where(Attendee.magic_access_token == token))
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    match = await db.get(Match, data.match_id)
    if not match or attendee.id not in (match.attendee_a_id, match.attendee_b_id):
        raise HTTPException(status_code=404, detail="Match not found")
    now = datetime.utcnow()
    if match.attendee_a_id == attendee.id:
        match.deferred_a_at = now
    else:
        match.deferred_b_at = now
    await db.commit()
    await db.refresh(match)
    return await _build_match_response(db, match, attendee.id)


@router.patch("/m/{token}/status", response_model=MatchResponse)
async def update_match_status_by_magic_link(
    token: str,
    data: MagicStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Magic-link accept/decline — no login required. Sets ONLY the caller's own
    side and recomputes the mutual state, so a no-login attendee can accept an
    incoming request back in one tap. Sends no email inline: the request path
    stays force-clean; mutual/pull-back notifications run off the request path
    (notify_pending_interest.py + the future cron)."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")
    if data.status not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="Status must be accepted or declined")
    result = await db.execute(select(Attendee).where(Attendee.magic_access_token == token))
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    match = await db.get(Match, data.match_id)
    if not match or attendee.id not in (match.attendee_a_id, match.attendee_b_id):
        raise HTTPException(status_code=404, detail="Match not found")
    if match.attendee_a_id == attendee.id:
        match.status_a = data.status
    else:
        match.status_b = data.status
    match.status = _compute_overall_status(match.status_a, match.status_b)
    if data.status == "declined":
        match.decline_reason = data.decline_reason
    await db.commit()
    await db.refresh(match)
    return await _build_match_response(db, match, attendee.id)


def _unsub_html(title: str, heading: str, body: str, link_href: str | None = None, link_label: str | None = None) -> str:
    """Minimal branded HTML page for unsubscribe/resubscribe confirmations."""
    cream = "#F6F4EF"
    terracotta = "#C2632A"
    ink = "#211500"
    muted = "#7A7268"
    link_block = ""
    if link_href and link_label:
        link_block = (
            f'<p style="margin:16px 0 0; font-size:14px; color:{muted};">'
            f'Changed your mind? <a href="{link_href}" style="color:{terracotta}; text-decoration:underline;">{link_label}</a>'
            f'</p>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ margin:0; padding:0; background:{cream}; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
  </style>
</head>
<body>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{cream}; min-height:100vh;">
    <tr><td align="center" style="padding:60px 20px;">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:100%; background:#ffffff; border-radius:8px; padding:48px 40px;">
        <tr><td>
          <div style="font-size:11px; font-weight:700; letter-spacing:0.16em; text-transform:uppercase; color:{terracotta}; margin-bottom:16px;">Proof of Talk 2026</div>
          <h1 style="margin:0 0 16px; font-size:24px; font-weight:600; color:{ink}; font-family:Georgia,'Times New Roman',serif;">{heading}</h1>
          <p style="margin:0; font-size:16px; line-height:1.6; color:{ink};">{body}</p>
          {link_block}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


@router.get("/m/{token}/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_via_magic_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe from engagement emails via magic link — no login required."""
    if not token or len(token) < 16:
        return HTMLResponse(
            _unsub_html(
                title="Invalid link",
                heading="This link is invalid",
                body="The unsubscribe link you followed is not recognised. If you believe this is an error, please reply to the email you received.",
            )
        )

    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token == token)
    )
    attendee = result.scalars().first()
    if not attendee:
        return HTMLResponse(
            _unsub_html(
                title="Invalid link",
                heading="This link is invalid",
                body="The unsubscribe link you followed is not recognised. If you believe this is an error, please reply to the email you received.",
            )
        )

    attendee.email_opt_out = True
    await db.commit()

    return HTMLResponse(
        _unsub_html(
            title="Unsubscribed",
            heading="You've been unsubscribed",
            body="You won't receive further matchmaking emails from Proof of Talk.",
            link_href=f"/api/v1/matches/m/{token}/resubscribe",
            link_label="Re-subscribe",
        )
    )


@router.get("/m/{token}/resubscribe", response_class=HTMLResponse)
async def resubscribe_via_magic_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Re-subscribe to engagement emails via magic link — no login required."""
    if not token or len(token) < 16:
        return HTMLResponse(
            _unsub_html(
                title="Invalid link",
                heading="This link is invalid",
                body="The re-subscribe link you followed is not recognised.",
            )
        )

    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token == token)
    )
    attendee = result.scalars().first()
    if not attendee:
        return HTMLResponse(
            _unsub_html(
                title="Invalid link",
                heading="This link is invalid",
                body="The re-subscribe link you followed is not recognised.",
            )
        )

    attendee.email_opt_out = False
    await db.commit()

    return HTMLResponse(
        _unsub_html(
            title="Resubscribed",
            heading="You're resubscribed",
            body="You'll receive matchmaking emails from Proof of Talk again.",
        )
    )


class MagicProfileUpdate(BaseModel):
    """Lightweight profile update via magic token (no JWT required)."""
    twitter_handle: str | None = None
    target_companies: str | None = None
    photo_url: str | None = None
    privacy_mode: str | None = None
    # Added 2026-05-12: Extasy buyers don't supply LinkedIn URL or goals
    # at checkout. Letting them self-fill via the magic link is the
    # cheapest fix for the 52 missing-LinkedIn attendees.
    linkedin_url: str | None = None
    goals: str | None = None


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
    if data.linkedin_url is not None:
        url = (data.linkedin_url or "").strip()
        # Light validation — must look like a LinkedIn profile URL
        if url and not (url.startswith("http") and "linkedin.com/in/" in url.lower()):
            raise HTTPException(status_code=400, detail="LinkedIn URL must be a linkedin.com/in/ profile link")
        attendee.linkedin_url = url or None
    if data.goals is not None:
        attendee.goals = (data.goals or "").strip() or None

    await db.commit()
    # Self-fill via magic link also unlocks/refreshes matches immediately.
    asyncio.create_task(refresh_profile_matches(attendee.id))
    return {"status": "updated"}


@router.post("/m/{token}/photo")
@limiter.limit("10/minute")
async def upload_photo_via_magic_link(
    request: Request,
    token: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a profile photo via magic link — no login required."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")
    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token == token)
    )
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    data = await file.read(MAX_BYTES + 1)
    try:
        url = await upload_avatar(str(attendee.id), data, file.content_type or "")
    except AvatarError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    attendee.photo_url = url
    await db.commit()
    return {"photo_url": url}


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

    # NOTE: mutual-match confirmation emails are no longer sent from this
    # request path. The reciprocity_notify cron (run_mutual_notifications,
    # every 2h) picks up status='accepted' + mutual_notified_at IS NULL and
    # sends to both parties with force=True. This removes the race condition
    # between the inline send and dedup, and keeps the request path clean.

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
    match.meeting_location = data.meeting_location or "Louvre Palace, Paris (exact spot shared at the venue)"

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
