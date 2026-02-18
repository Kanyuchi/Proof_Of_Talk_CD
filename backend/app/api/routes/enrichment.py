from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.attendee import Attendee
from app.services.enrichment import EnrichmentService
from app.services.embeddings import generate_ai_summary, embed_attendee, classify_intents
from app.core.deps import require_auth, require_admin
from app.models.user import User

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.get("/{attendee_id}/status")
async def enrichment_status(attendee_id: UUID, db: AsyncSession = Depends(get_db), _user: User = Depends(require_auth)):
    """Return per-source enrichment status for an attendee."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    ep = attendee.enriched_profile or {}
    pot = attendee.pot_history or {}
    cb = attendee.crunchbase_data or {}

    def src_status(key: str, enriched_at_key: str, has_input: bool) -> dict:
        data = ep.get(key)
        return {
            "available": bool(data),
            "enriched_at": ep.get(enriched_at_key),
            "configured": has_input,
        }

    return {
        "attendee_id": str(attendee_id),
        "last_enriched": attendee.enriched_at.isoformat() if attendee.enriched_at else None,
        "ai_summary": bool(attendee.ai_summary),
        "embedding": attendee.embedding is not None,
        "sources": {
            "registration": {
                "available": True,
                "configured": True,
                "enriched_at": attendee.created_at.isoformat(),
            },
            "linkedin": src_status("linkedin", "linkedin_enriched_at", bool(attendee.linkedin_url)),
            "twitter": src_status("twitter", "twitter_enriched_at", bool(attendee.twitter_handle)),
            "website": src_status("website", "website_enriched_at", bool(attendee.company_website)),
            "crunchbase": {
                "available": bool(ep.get("crunchbase") or cb),
                "enriched_at": ep.get("crunchbase_enriched_at"),
                "configured": True,  # always attempted via company name
            },
            "pot_history": {
                "available": bool(pot.get("events")),
                "enriched_at": None,
                "configured": True,
            },
        },
        "data": {
            "linkedin_summary": ep.get("linkedin_summary"),
            "recent_activity": ep.get("recent_activity"),
            "company_description": ep.get("company_description"),
            "crunchbase": ep.get("crunchbase") or cb or None,
            "pot_history": pot,
            "intent_tags": attendee.intent_tags or [],
            "deal_readiness_score": attendee.deal_readiness_score,
        },
    }


@router.post("/{attendee_id}")
async def enrich_attendee(attendee_id: UUID, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """Trigger data enrichment for a single attendee."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    service = EnrichmentService()
    try:
        enriched = await service.enrich_attendee(attendee)
        attendee.enriched_profile = enriched
        attendee.enriched_at = datetime.utcnow()

        # Regenerate AI fields after enrichment
        attendee.ai_summary = await generate_ai_summary(attendee)
        attendee.intent_tags = await classify_intents(attendee)
        attendee.embedding = await embed_attendee(attendee)

        await db.commit()
        return {
            "status": "completed",
            "attendee_id": str(attendee_id),
            "sources_enriched": [k for k in enriched.keys() if not k.endswith("_at") and not k.endswith("_summary") and not k.endswith("_description") and not k.endswith("_activity")],
        }
    finally:
        await service.close()


@router.post("/batch")
async def enrich_all(db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """Batch enrich all attendees."""
    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()

    service = EnrichmentService()
    results = []
    try:
        for attendee in attendees:
            enriched = await service.enrich_attendee(attendee)
            attendee.enriched_profile = enriched
            attendee.enriched_at = datetime.utcnow()
            attendee.ai_summary = await generate_ai_summary(attendee)
            attendee.intent_tags = await classify_intents(attendee)
            attendee.embedding = await embed_attendee(attendee)
            results.append({"attendee_id": str(attendee.id), "sources": list(enriched.keys())})

        await db.commit()
        return {"status": "completed", "results": results}
    finally:
        await service.close()
