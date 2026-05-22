"""Detached profile-enrichment + match-refresh triggers.

Two functions, run via asyncio.create_task (NOT FastAPI BackgroundTasks —
that holds the request worker through a 10-20s OpenAI/Grid pipeline and 504s
the edge):

- refresh_profile_matches: LIGHT path. Re-embed from the current profile and
  regenerate matches. No re-scraping. Used by every profile save and as
  stages 2-3 of the cold-start join.
- run_full_enrichment: COLD-START path. Grid + website enrichment, then
  refresh_profile_matches. Used by the sponsor join (no enrichment data yet).
"""
import logging
import uuid

from app.core.database import async_session
from app.models.attendee import Attendee
from app.services.matching import MatchingEngine
from app.services.enrichment import EnrichmentService

logger = logging.getLogger(__name__)


async def refresh_profile_matches(attendee_id: uuid.UUID, notify: bool = False) -> None:
    try:
        async with async_session() as db:
            engine = MatchingEngine(db)
            attendee = await db.get(Attendee, attendee_id)
            if not attendee:
                return
            await engine.process_attendee(attendee)
            # notify defaults False: saves shouldn't spam match emails; callers may opt in.
            await engine.generate_matches_for_attendee(
                attendee_id, top_k=10, notify=notify
            )
    except Exception as exc:
        logger.exception("refresh_profile_matches failed for %s: %s", attendee_id, exc)


async def run_full_enrichment(attendee_id: uuid.UUID) -> None:
    try:
        async with async_session() as db:
            attendee = await db.get(Attendee, attendee_id)
            if not attendee:
                return
            try:
                svc = EnrichmentService()
                # enrich_attendee returns a NEW dict; assigning it is required
                # for SQLAlchemy to detect the JSONB change (mutate-and-reassign
                # the same ref is a silent no-op).
                attendee.enriched_profile = await svc.enrich_attendee(attendee)
                await db.commit()
            except Exception:
                logger.exception(
                    "run_full_enrichment: enrich stage failed for %s", attendee_id
                )
    except Exception as exc:
        logger.exception("run_full_enrichment outer failure for %s: %s", attendee_id, exc)
    # Always attempt the embed + match refresh, even if the enrich stage failed.
    await refresh_profile_matches(attendee_id)
