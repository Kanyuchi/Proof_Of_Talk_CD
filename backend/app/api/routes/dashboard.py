from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.attendee import Attendee, Match
from app.schemas.attendee import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
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
async def match_quality(db: AsyncSession = Depends(get_db)):
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
