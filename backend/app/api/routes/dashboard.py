import csv
import io
from collections import defaultdict

import httpx
import structlog
logger = structlog.get_logger(__name__)
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import get_settings
from app.models.attendee import Attendee, Match
from app.schemas.attendee import DashboardStats
from app.core.deps import require_auth, require_admin
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
settings = get_settings()


def _compute_kpi_rates(
    matches_generated: int,
    mutual_accepted_count: int,
    scheduled_count: int,
    show_count: int,
) -> tuple[float, float, float]:
    mutual_accept_rate = (mutual_accepted_count / matches_generated) if matches_generated else 0.0
    scheduled_rate = (scheduled_count / mutual_accepted_count) if mutual_accepted_count else 0.0
    show_rate = (show_count / scheduled_count) if scheduled_count else 0.0
    return mutual_accept_rate, scheduled_rate, show_rate


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """Organiser dashboard: event-wide stats."""
    total_attendees = (await db.execute(select(func.count(Attendee.id)))).scalar() or 0

    # Exclude matches involving admin-linked attendees so demo/test accounts don't skew stats
    admin_attendee_subq = (
        select(User.attendee_id)
        .where(and_(User.is_admin.is_(True), User.attendee_id.isnot(None)))
        .scalar_subquery()
    )
    non_admin_filter = and_(
        ~Match.attendee_a_id.in_(admin_attendee_subq),
        ~Match.attendee_b_id.in_(admin_attendee_subq),
    )
    mutual_filter = and_(
        non_admin_filter,
        Match.status_a.in_(["accepted", "met"]),
        Match.status_b.in_(["accepted", "met"]),
    )

    matches_generated = (
        await db.execute(select(func.count(Match.id)).where(non_admin_filter))
    ).scalar() or 0
    # matches_accepted = mutual accepts (both sides said yes), consistent with mutual_accepted_count
    matches_accepted = (
        await db.execute(select(func.count(Match.id)).where(mutual_filter))
    ).scalar() or 0
    matches_declined = (
        await db.execute(
            select(func.count(Match.id)).where(
                and_(non_admin_filter, Match.status == "declined")
            )
        )
    ).scalar() or 0
    mutual_accepted_count = matches_accepted  # same query — reuse
    scheduled_count = (
        await db.execute(
            select(func.count(Match.id)).where(
                and_(non_admin_filter, Match.meeting_time.isnot(None))
            )
        )
    ).scalar() or 0
    show_count = (
        await db.execute(
            select(func.count(Match.id)).where(
                and_(
                    non_admin_filter,
                    (Match.met_at.isnot(None)) | (Match.status == "met") | (Match.meeting_outcome == "met"),
                )
            )
        )
    ).scalar() or 0

    # Enrichment coverage: % of attendees with AI summary
    enriched_count = (
        await db.execute(
            select(func.count(Attendee.id)).where(
                Attendee.ai_summary.isnot(None)
            )
        )
    ).scalar() or 0
    enrichment_coverage = enriched_count / total_attendees if total_attendees > 0 else 0.0

    # Average match score (non-admin matches only)
    avg_score = (
        await db.execute(select(func.avg(Match.overall_score)).where(non_admin_filter))
    ).scalar() or 0.0
    avg_satisfaction = (
        await db.execute(select(func.avg(Match.satisfaction_score)).where(Match.satisfaction_score.isnot(None)))
    ).scalar() or 0.0

    # Match type distribution (non-admin matches only)
    type_result = await db.execute(
        select(Match.match_type, func.count(Match.id))
        .where(non_admin_filter)
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
    mutual_accept_rate, scheduled_rate, show_rate = _compute_kpi_rates(
        matches_generated=matches_generated,
        mutual_accepted_count=mutual_accepted_count,
        scheduled_count=scheduled_count,
        show_count=show_count,
    )

    return DashboardStats(
        total_attendees=total_attendees,
        matches_generated=matches_generated,
        matches_accepted=matches_accepted,
        matches_declined=matches_declined,
        enrichment_coverage=enrichment_coverage,
        avg_match_score=float(avg_score),
        mutual_accept_rate=mutual_accept_rate,
        scheduled_rate=scheduled_rate,
        show_rate=show_rate,
        post_meeting_satisfaction=float(avg_satisfaction or 0.0),
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


@router.post("/sync-extasy")
async def sync_extasy(
    _admin: User = Depends(require_admin),
):
    """Admin: pull confirmed (PAID) attendees from Extasy, upsert into DB, then enrich new attendees."""
    from app.services.extasy_sync import sync_and_enrich
    result = await sync_and_enrich()
    return {"status": "completed", **result}


@router.post("/sync-speakers")
async def sync_speakers(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Admin: pull speakers from 1000 Minds table and upsert into attendees for matching."""
    from app.services.speakers_sync import sync_speakers_to_attendees
    result = await sync_speakers_to_attendees(db)
    return {"status": "completed", **result}


@router.get("/engagement/nudges/dry-run")
async def nudge_dry_run(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Preview currently due engagement nudges without dispatching them."""
    if not settings.AI_NUDGE_ENABLED:
        return {"status": "disabled", "reason": "Set AI_NUDGE_ENABLED=true to enable nudges"}
    from app.services.engagement import trigger_nudges
    return await trigger_nudges(db, dry_run=True)


@router.post("/engagement/nudges/trigger")
async def nudge_trigger(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Dispatch due nudges (idempotent by daily dedup key)."""
    if not settings.AI_NUDGE_ENABLED:
        return {"status": "disabled", "reason": "Set AI_NUDGE_ENABLED=true to enable nudges"}
    from app.services.engagement import trigger_nudges
    return await trigger_nudges(db, dry_run=False)


@router.get("/investor-heatmap")
async def investor_heatmap(db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """Investor activity heatmap: vertical_tags × intent signals for capital deployers."""
    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()

    # All 11 verticals
    ALL_VERTICALS = [
        "tokenisation_of_finance", "infrastructure_and_scaling", "decentralized_finance",
        "ai_depin_frontier_tech", "policy_regulation_macro", "ecosystem_and_foundations",
        "investment_and_capital_markets", "culture_media_gaming", "bitcoin",
        "prediction_markets", "decentralized_ai",
    ]
    CAPITAL_INTENTS = {"deploying_capital", "co_investment", "deal_making"}

    # Build heatmap: for each vertical, count attendees and capital-active attendees
    heatmap = []
    for vertical in ALL_VERTICALS:
        in_vertical = [a for a in attendees if vertical in (a.vertical_tags or [])]
        capital_active = [a for a in in_vertical if CAPITAL_INTENTS & set(a.intent_tags or [])]
        avg_deal = (
            sum(a.deal_readiness_score or 0 for a in in_vertical) / len(in_vertical)
            if in_vertical else 0.0
        )
        heatmap.append({
            "vertical": vertical,
            "label": vertical.replace("_", " ").title(),
            "attendee_count": len(in_vertical),
            "capital_active": len(capital_active),
            "avg_deal_readiness": round(avg_deal, 2),
        })

    # Sort by capital_active descending
    heatmap.sort(key=lambda x: x["capital_active"], reverse=True)

    # Deal readiness distribution
    high = sum(1 for a in attendees if (a.deal_readiness_score or 0) >= 0.75)
    medium = sum(1 for a in attendees if 0.4 <= (a.deal_readiness_score or 0) < 0.75)
    low = sum(1 for a in attendees if (a.deal_readiness_score or 0) < 0.4)

    return {
        "heatmap": heatmap,
        "total_attendees": len(attendees),
        "deal_readiness_distribution": {"high": high, "medium": medium, "low": low},
    }


@router.get("/grid-health")
async def grid_health_check(
    _admin: User = Depends(require_admin),
):
    """Check if The Grid B2B API is reachable and working correctly."""
    from app.services.grid_enrichment import health_check
    return await health_check()


async def _re_enrich_grid_job() -> dict:
    """Long-running Grid re-enrichment — runs in background via jobs service.

    Uses its own DB session (the request-scoped session is closed by the time
    the background task runs).
    """
    from datetime import datetime as _dt
    from app.services.grid_enrichment import enrich_from_grid
    from app.core.database import async_session

    async with async_session() as db:
        result = await db.execute(select(Attendee).where(Attendee.company.isnot(None)))
        attendees = result.scalars().all()

        enriched_count = 0
        skipped = 0
        failed = 0

        for attendee in attendees:
            enriched = attendee.enriched_profile or {}
            if enriched.get("grid", {}).get("grid_name"):
                skipped += 1
                continue
            try:
                grid_data = await enrich_from_grid(attendee.company, attendee.company_website)
                if grid_data:
                    enriched["grid"] = grid_data
                    enriched["grid_enriched_at"] = _dt.utcnow().isoformat()
                    enriched_count += 1
                else:
                    enriched["grid_attempted_at"] = _dt.utcnow().isoformat()
                    failed += 1
                attendee.enriched_profile = enriched
                db.add(attendee)
            except Exception:
                failed += 1

        await db.commit()
        return {
            "status": "done",
            "total": len(attendees),
            "already_enriched": skipped,
            "newly_enriched": enriched_count,
            "not_found": failed,
        }


@router.post("/re-enrich-grid", status_code=202)
async def re_enrich_grid(
    _admin: User = Depends(require_admin),
):
    """Kick off Grid re-enrichment as a background job. Returns immediately.

    Poll GET /dashboard/jobs/{job_id} for progress + result.
    """
    from app.services.jobs import submit
    job_id = submit("re_enrich_grid", _re_enrich_grid_job)
    return {"job_id": job_id, "status": "pending", "kind": "re_enrich_grid"}


EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_ORDERS_URL = f"https://api.b2b.extasy.com/operations/reports/orders/{EXTASY_EVENT_ID}"
TEST_TICKET_NAMES = {"test ticket", "test ticket card"}


@router.get("/revenue")
async def revenue_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Revenue tracking, registration funnel, and attendee growth from Extasy."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(EXTASY_ORDERS_URL)
            resp.raise_for_status()
            text = resp.content.decode("iso-8859-1", errors="replace")
            orders = list(csv.DictReader(io.StringIO(text)))
    except Exception as exc:
        return {"error": f"Extasy API unavailable: {exc}"}

    # ── Registration funnel ───────────────────────────────────────────────
    funnel = defaultdict(int)
    for o in orders:
        funnel[o.get("status", "UNKNOWN")] += 1
    total_orders = len(orders)
    paid = funnel.get("PAID", 0)
    redeemed = funnel.get("REDEEMED", 0)
    failed = funnel.get("FAILED", 0)
    refunded = funnel.get("REFUNDED", 0)
    pending = funnel.get("PAYMENT_PENDING", 0)
    valid = paid + redeemed
    conversion_rate = valid / total_orders if total_orders else 0

    # ── Revenue ───────────────────────────────────────────────────────────
    # Deduplicate true duplicate orders: same email + same ticket + same
    # amount (e.g. accidental re-purchase).  Keeps legitimate multi-ticket
    # purchases where the same email bought different ticket types.
    _valid_raw = [o for o in orders if o.get("status") in {"PAID", "REDEEMED"}]
    _dedup_seen: set[tuple[str, str, str]] = set()
    valid_orders: list[dict] = []
    for o in _valid_raw:
        email = (o.get("email") or "").strip().lower()
        ticket = (o.get("ticketNames") or "").split(",")[0].strip().lower()
        amount = (o.get("paymentsAmount") or "0").strip()
        key = (email, ticket, amount)
        if key in _dedup_seen:
            continue
        _dedup_seen.add(key)
        valid_orders.append(o)

    total_revenue = 0.0
    revenue_by_type = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    paid_count = 0
    comp_count = 0

    for o in valid_orders:
        ticket_name = (o.get("ticketNames") or "").split(",")[0].strip()
        if ticket_name.lower() in TEST_TICKET_NAMES:
            continue

        amount = 0.0
        try:
            amount = float(o.get("paymentsAmount") or o.get("fullPrice") or "0")
        except (ValueError, TypeError):
            pass

        total_revenue += amount
        revenue_by_type[ticket_name]["count"] += 1
        revenue_by_type[ticket_name]["revenue"] += amount

        if amount > 0:
            paid_count += 1
        else:
            comp_count += 1

    real_valid = sum(t["count"] for t in revenue_by_type.values())
    avg_ticket = total_revenue / paid_count if paid_count else 0

    # ── Growth over time (weekly buckets) ─────────────────────────────────
    from datetime import datetime
    weekly = defaultdict(int)
    for o in valid_orders:
        ticket_name = (o.get("ticketNames") or "").split(",")[0].strip()
        if ticket_name.lower() in TEST_TICKET_NAMES:
            continue
        created = o.get("createdAtUtc", "")
        if created:
            try:
                dt = datetime.strptime(created[:10], "%Y-%m-%d")
                # ISO week label
                week = dt.strftime("%Y-W%V")
                weekly[week] += 1
            except ValueError:
                pass
    growth = [{"week": w, "registrations": c} for w, c in sorted(weekly.items())]

    # ── Profile completeness from DB ──────────────────────────────────────
    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()
    total_db = len(attendees)
    with_goals = sum(1 for a in attendees if a.goals)
    with_linkedin = sum(1 for a in attendees if a.linkedin_url)
    with_twitter = sum(1 for a in attendees if a.twitter_handle)
    with_website = sum(1 for a in attendees if a.company_website)
    with_grid = sum(1 for a in attendees if (a.enriched_profile or {}).get("grid", {}).get("grid_name"))
    with_photo = sum(1 for a in attendees if a.photo_url)
    with_targets = sum(1 for a in attendees if a.target_companies)

    # ── Source breakdown ──────────────────────────────────────────────────
    from_extasy = sum(1 for a in attendees if "extasy" in str(a.enriched_profile or ""))
    from_speakers = sum(1 for a in attendees if a.email and "speaker.proofoftalk.io" in a.email)
    from_seed = sum(1 for a in attendees if a.email and "@example.com" in a.email)
    from_other = total_db - from_extasy - from_speakers - from_seed

    return {
        "funnel": {
            "total_orders": total_orders,
            "paid": paid,
            "redeemed": redeemed,
            "failed": failed,
            "refunded": refunded,
            "pending": pending,
            "valid": valid,
            "conversion_rate": round(conversion_rate, 3),
        },
        "revenue": {
            "total": round(total_revenue, 2),
            "avg_ticket_price": round(avg_ticket, 2),
            "paid_tickets": paid_count,
            "comp_tickets": comp_count,
            "by_type": [
                {"type": k, "count": v["count"], "revenue": round(v["revenue"], 2)}
                for k, v in sorted(revenue_by_type.items(), key=lambda x: -x[1]["revenue"])
            ],
        },
        "growth": growth,
        "source_breakdown": {
            "extasy": from_extasy,
            "speakers_1000minds": from_speakers,
            "seed": from_seed,
            "other": from_other,
            "total": total_db,
        },
        "profile_completeness": {
            "total": total_db,
            "with_goals": with_goals,
            "with_linkedin": with_linkedin,
            "with_twitter": with_twitter,
            "with_website": with_website,
            "with_grid": with_grid,
            "with_photo": with_photo,
            "with_targets": with_targets,
        },
    }


# ── Sponsor Intelligence ──────────────────────────────────────────────────

@router.get("/sponsors")
async def list_sponsors(
    _admin: User = Depends(require_admin),
):
    """List all 24 POT 2026 sponsors."""
    from app.services.sponsor_intelligence import SPONSORS
    return {"sponsors": SPONSORS}


@router.post("/sponsor-report", status_code=202)
async def generate_sponsor_report(
    body: dict,
    _admin: User = Depends(require_admin),
):
    """Kick off sponsor intelligence report as a background job.

    Returns 202 with job_id immediately. Poll /dashboard/jobs/{job_id} for the
    full report once status == "done".
    """
    company_name = body.get("company_name")
    if not company_name:
        return {"error": "company_name is required"}

    top_k = body.get("top_k", 20)
    identify_team = body.get("identify_team", True)

    async def _sponsor_job() -> dict:
        from app.services.sponsor_intelligence import run_sponsor_report
        from app.core.database import async_session
        async with async_session() as db:
            return await run_sponsor_report(
                sponsor_name=company_name,
                db=db,
                top_k=top_k,
                identify_team=identify_team,
            )

    from app.services.jobs import submit
    job_id = submit(
        "sponsor_report",
        _sponsor_job,
        metadata={"company_name": company_name},
    )
    return {"job_id": job_id, "status": "pending", "kind": "sponsor_report"}


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    _admin: User = Depends(require_admin),
):
    """Get status + result of a background job."""
    from app.services.jobs import get as jobs_get
    job = jobs_get(job_id)
    if not job:
        return {"error": "job not found", "job_id": job_id}
    return job


@router.get("/jobs")
async def list_recent_jobs(
    limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
):
    """List recent background jobs (for admin debugging)."""
    from app.services.jobs import list_recent
    return {"jobs": list_recent(limit=limit)}
