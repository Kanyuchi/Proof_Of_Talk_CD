import structlog
logger = structlog.get_logger(__name__)
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.attendee import Attendee, Match
from app.schemas.attendee import DashboardStats
from app.core.deps import require_auth, require_admin
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """Organiser dashboard: event-wide stats."""
    total_attendees = (await db.execute(select(func.count(Attendee.id)))).scalar() or 0
    matches_generated = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    matches_accepted = (
        await db.execute(
            select(func.count(Match.id)).where(Match.status == "accepted")
        )
    ).scalar() or 0
    matches_declined = (
        await db.execute(
            select(func.count(Match.id)).where(Match.status == "declined")
        )
    ).scalar() or 0

    # Enrichment coverage: % of attendees with non-empty enriched_profile
    enriched_count = (
        await db.execute(
            select(func.count(Attendee.id)).where(
                Attendee.ai_summary.isnot(None)
            )
        )
    ).scalar() or 0
    enrichment_coverage = enriched_count / total_attendees if total_attendees > 0 else 0.0

    # Average match score
    avg_score = (
        await db.execute(select(func.avg(Match.overall_score)))
    ).scalar() or 0.0

    # Match type distribution
    type_result = await db.execute(
        select(Match.match_type, func.count(Match.id))
        .group_by(Match.match_type)
    )
    match_type_distribution = {row[0]: row[1] for row in type_result.fetchall()}

    # Top sectors from attendee interests (flatten and count)
    attendees_result = await db.execute(select(Attendee.interests))
    all_interests = []
    for row in attendees_result.fetchall():
        if row[0]:
            all_interests.extend(row[0])

    from collections import Counter
    interest_counts = Counter(all_interests).most_common(10)
    top_sectors = [{"sector": s, "count": c} for s, c in interest_counts]

    return DashboardStats(
        total_attendees=total_attendees,
        matches_generated=matches_generated,
        matches_accepted=matches_accepted,
        matches_declined=matches_declined,
        enrichment_coverage=enrichment_coverage,
        avg_match_score=float(avg_score),
        top_sectors=top_sectors,
        match_type_distribution=match_type_distribution,
    )


@router.get("/match-quality")
async def match_quality(db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """Match quality distribution and analytics."""
    result = await db.execute(
        select(Match.overall_score, Match.match_type, Match.status)
    )
    matches = result.fetchall()

    # Bucket scores into ranges
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for score, _, _ in matches:
        if score < 0.2:
            buckets["0.0-0.2"] += 1
        elif score < 0.4:
            buckets["0.2-0.4"] += 1
        elif score < 0.6:
            buckets["0.4-0.6"] += 1
        elif score < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1

    return {
        "total_matches": len(matches),
        "score_distribution": buckets,
        "acceptance_rate": (
            sum(1 for _, _, s in matches if s == "accepted") / len(matches)
            if matches
            else 0.0
        ),
    }


@router.get("/matches-by-type")
async def matches_by_type(
    match_type: str = Query(...),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Drill-down: return matches of a given type with attendee names."""
    result = await db.execute(
        select(Match)
        .where(Match.match_type == match_type)
        .order_by(Match.overall_score.desc())
        .limit(limit)
    )
    raw = result.scalars().all()

    matches_out = []
    for m in raw:
        attendee_a = await db.get(Attendee, m.attendee_a_id)
        attendee_b = await db.get(Attendee, m.attendee_b_id)
        pair_label = "Unknown pair"
        if attendee_a and attendee_b:
            pair_label = f"{attendee_a.name} ↔ {attendee_b.name}"

        matches_out.append(
            {
                "id": str(m.id),
                "overall_score": float(m.overall_score),
                "explanation": m.explanation,
                "match_type": m.match_type,
                "status": m.status,
                "attendee_a_id": str(m.attendee_a_id),
                "attendee_b_id": str(m.attendee_b_id),
                "matched_attendee": {
                    "id": str(m.id),
                    "name": pair_label,
                },
            }
        )

    return {"matches": matches_out, "total": len(matches_out)}


@router.get("/feedback-dataset")
async def feedback_dataset(
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Export match outcomes for analytics / training pipelines."""
    result = await db.execute(
        select(Match)
        .where(
            (Match.decline_reason.isnot(None))
            | (Match.meeting_outcome.isnot(None))
            | (Match.satisfaction_score.isnot(None))
        )
        .order_by(Match.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    dataset = []
    for m in rows:
        attendee_a = await db.get(Attendee, m.attendee_a_id)
        attendee_b = await db.get(Attendee, m.attendee_b_id)
        dataset.append(
            {
                "match_id": str(m.id),
                "attendee_a_id": str(m.attendee_a_id),
                "attendee_a_name": attendee_a.name if attendee_a else None,
                "attendee_b_id": str(m.attendee_b_id),
                "attendee_b_name": attendee_b.name if attendee_b else None,
                "match_type": m.match_type,
                "overall_score": float(m.overall_score),
                "status": m.status,
                "decline_reason": m.decline_reason,
                "meeting_time": m.meeting_time.isoformat() if m.meeting_time else None,
                "met_at": m.met_at.isoformat() if m.met_at else None,
                "meeting_outcome": m.meeting_outcome,
                "satisfaction_score": m.satisfaction_score,
                "explanation_confidence": m.explanation_confidence,
                "created_at": m.created_at.isoformat(),
            }
        )
    return {"rows": dataset, "total": len(dataset)}


@router.get("/attendees-by-sector")
async def attendees_by_sector(
    sector: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Drill-down: return attendees whose interests include a given sector."""
    result = await db.execute(select(Attendee))
    all_attendees = result.scalars().all()

    matching = [a for a in all_attendees if a.interests and sector in a.interests]

    return {
        "attendees": [
            {
                "id": str(a.id),
                "name": a.name,
                "title": a.title,
                "company": a.company,
            }
            for a in matching
        ],
        "total": len(matching),
    }


@router.post("/trigger-processing")
async def trigger_processing(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: re-generate AI summaries + embeddings for all attendees."""
    from app.services.enrichment import enrich_attendee

    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()

    async def process_all():
        from app.core.database import async_session
        async with async_session() as session:
            for a in attendees:
                try:
                    await enrich_attendee(str(a.id), session)
                except Exception as exc:
                    logger.error("bg_enrich_failed", attendee_id=str(a.id), error=str(exc))

    background_tasks.add_task(process_all)
    return {"status": "started", "attendees_processed": len(attendees)}


@router.post("/trigger-matching")
async def trigger_matching(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: re-run the full matching pipeline."""
    from app.services.matching import run_matching_pipeline

    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()
    top_k = max(1, min(len(attendees) - 1, 10)) if attendees else 1

    async def run_pipeline():
        from app.core.database import async_session
        async with async_session() as session:
            try:
                await run_matching_pipeline(session, top_k=top_k)
            except Exception as exc:
                logger.error("bg_matching_failed", error=str(exc))

    background_tasks.add_task(run_pipeline)
    return {
        "status": "started",
        "attendees_processed": len(attendees),
        "top_k": top_k,
        "total_matches": len(attendees) * top_k,
    }
