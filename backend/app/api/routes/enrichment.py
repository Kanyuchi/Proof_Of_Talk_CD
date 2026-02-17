from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.attendee import Attendee
from app.services.enrichment import EnrichmentService
from app.services.embeddings import generate_ai_summary, embed_attendee, classify_intents

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/{attendee_id}")
async def enrich_attendee(attendee_id: UUID, db: AsyncSession = Depends(get_db)):
    """Trigger data enrichment for a single attendee."""
    attendee = await db.get(Attendee, attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    service = EnrichmentService()
    try:
        enriched = await service.enrich_attendee(attendee)
        attendee.enriched_profile = enriched

        # Regenerate AI fields after enrichment
        attendee.ai_summary = await generate_ai_summary(attendee)
        attendee.intent_tags = await classify_intents(attendee)
        attendee.embedding = await embed_attendee(attendee)

        await db.commit()
        return {
            "status": "completed",
            "attendee_id": str(attendee_id),
            "sources_enriched": list(enriched.keys()),
        }
    finally:
        await service.close()


@router.post("/batch")
async def enrich_all(db: AsyncSession = Depends(get_db)):
    """Batch enrich all attendees."""
    result = await db.execute(select(Attendee))
    attendees = result.scalars().all()

    service = EnrichmentService()
    results = []
    try:
        for attendee in attendees:
            enriched = await service.enrich_attendee(attendee)
            attendee.enriched_profile = enriched
            attendee.ai_summary = await generate_ai_summary(attendee)
            attendee.intent_tags = await classify_intents(attendee)
            attendee.embedding = await embed_attendee(attendee)
            results.append({"attendee_id": str(attendee.id), "sources": list(enriched.keys())})

        await db.commit()
        return {"status": "completed", "results": results}
    finally:
        await service.close()
