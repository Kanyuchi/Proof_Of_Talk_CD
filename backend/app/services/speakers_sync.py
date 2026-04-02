"""
1000 Minds speakers → Matchmaker attendees sync
================================================
Reads from the `speakers` table (managed by 1000 Minds / Jessica) in the
same Supabase database, and upserts each speaker into the `attendees` table
for matching.

Data flows ONE direction: speakers → attendees. The matchmaker never writes
back to the speakers table.

Called from POST /api/v1/dashboard/sync-speakers (admin only) and daily cron.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Attendee, TicketType

logger = logging.getLogger(__name__)

# ── Seniority → TicketType mapping ────────────────────────────────────────────
SENIORITY_MAP: dict[str, str] = {
    "c-level": "vip",
    "founder": "vip",
    "partner": "speaker",
    "head of": "speaker",
    "director": "speaker",
    "vp": "speaker",
    "manager": "delegate",
}


def _map_seniority_to_ticket(seniority: str | None) -> TicketType:
    if not seniority:
        return TicketType.SPEAKER  # default for speakers
    key = seniority.strip().lower()
    mapped = SENIORITY_MAP.get(key, "speaker")
    return TicketType(mapped)


def _region_to_geographies(region: str | None) -> list[str]:
    if not region:
        return []
    return [region.strip()]


# ── Main sync function ────────────────────────────────────────────────────────

async def sync_speakers_to_attendees(db: AsyncSession) -> dict:
    """
    Read all speakers from the speakers table and upsert into attendees.
    Deduplicates by name+company (speakers table has no email field).

    Returns dict with sync stats:
        total_speakers, inserted, updated, skipped, errors
    """
    logger.info("speakers_sync: reading speakers table")

    # Read directly from the speakers table (same Supabase DB)
    try:
        result = await db.execute(
            text("SELECT * FROM speakers WHERE is_live = true ORDER BY name")
        )
        rows = result.mappings().all()
    except Exception as exc:
        logger.error("speakers_sync: failed to read speakers table: %s", exc)
        raise RuntimeError(f"Failed to read speakers table: {exc}") from exc

    total = len(rows)
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    for speaker in rows:
        try:
            name = (speaker.get("name") or "").strip()
            company = (speaker.get("company") or "").strip()
            title = (speaker.get("title") or "").strip()

            if not name:
                skipped += 1
                continue

            # Dedup: check if an attendee with this name+company already exists
            existing = (
                await db.execute(
                    select(Attendee).where(
                        Attendee.name.ilike(name),
                        Attendee.company.ilike(company) if company else True,
                    )
                )
            ).scalars().first()

            bio = (speaker.get("bio") or "").strip()
            verticals = speaker.get("verticals") or []
            region = speaker.get("region") or ""
            seniority = speaker.get("seniority") or ""
            image_url = speaker.get("image_url") or None
            grid_slug = speaker.get("grid_slug") or None

            if existing:
                # Update fields that might be richer from speakers table
                changed = False
                if bio and (not existing.goals or len(bio) > len(existing.goals or "")):
                    existing.goals = bio
                    changed = True
                if verticals and not existing.vertical_tags:
                    # Map display names to slugs
                    existing.vertical_tags = [_vertical_to_slug(v) for v in verticals]
                    changed = True
                if image_url and not existing.photo_url:
                    existing.photo_url = image_url
                    changed = True
                if region and not existing.preferred_geographies:
                    existing.preferred_geographies = _region_to_geographies(region)
                    changed = True
                if changed:
                    updated += 1
                else:
                    skipped += 1
                continue

            # Create new attendee from speaker
            # Generate a placeholder email from name (speakers table has no email)
            slug = name.lower().replace(" ", ".").replace(",", "")
            placeholder_email = f"{slug}@speaker.proofoftalk.io"

            attendee = Attendee(
                name=name,
                email=placeholder_email,
                company=company,
                title=title,
                ticket_type=_map_seniority_to_ticket(seniority),
                goals=bio if bio else None,
                vertical_tags=[_vertical_to_slug(v) for v in verticals] if verticals else [],
                preferred_geographies=_region_to_geographies(region),
                photo_url=image_url,
                interests=[],
                seeking=[],
                not_looking_for=[],
            )
            db.add(attendee)
            await db.flush()
            inserted += 1
            logger.info("speakers_sync: inserted %s (%s @ %s)", name, title, company)

        except Exception as exc:
            errors += 1
            logger.warning("speakers_sync: error processing speaker %s: %s", speaker.get("name"), exc)
            await db.rollback()

    await db.commit()

    stats = {
        "total_speakers": total,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }
    logger.info("speakers_sync: complete — %s", stats)
    return stats


# ── Vertical display name → slug mapping ──────────────────────────────────────

VERTICAL_SLUG_MAP = {
    "tokenisation of finance": "tokenisation_of_finance",
    "infrastructure & scaling": "infrastructure_and_scaling",
    "infrastructure and scaling": "infrastructure_and_scaling",
    "decentralized finance": "decentralized_finance",
    "defi": "decentralized_finance",
    "ai, depin & frontier tech": "ai_depin_frontier_tech",
    "ai depin frontier tech": "ai_depin_frontier_tech",
    "policy, regulation & macro": "policy_regulation_macro",
    "policy regulation macro": "policy_regulation_macro",
    "ecosystem & foundations": "ecosystem_and_foundations",
    "ecosystem and foundations": "ecosystem_and_foundations",
    "investment & capital markets": "investment_and_capital_markets",
    "investment and capital markets": "investment_and_capital_markets",
    "culture, media & gaming": "culture_media_gaming",
    "culture media gaming": "culture_media_gaming",
    "bitcoin": "bitcoin",
    "prediction markets": "prediction_markets",
    "decentralized ai": "decentralized_ai",
    "privacy": "privacy",
}


def _vertical_to_slug(display_name: str) -> str:
    key = display_name.strip().lower()
    return VERTICAL_SLUG_MAP.get(key, key.replace(" ", "_").replace(",", "").replace("&", "and"))


# ── Combined sync + enrich ────────────────────────────────────────────────────

async def sync_and_enrich() -> dict:
    """Sync speakers then trigger enrichment for newly inserted attendees."""
    from app.core.database import async_session

    async with async_session() as db:
        stats = await sync_speakers_to_attendees(db)

    # If new attendees were inserted, trigger enrichment
    if stats["inserted"] > 0:
        logger.info("speakers_sync: triggering enrichment for %d new attendees", stats["inserted"])
        # Enrichment happens via the daily cron or manual trigger — not blocking here

    return stats
