"""
Extasy → RDS sync service
=========================
Fetches PAID orders from the Extasy ticketing API and upserts them into
the PostgreSQL database via SQLAlchemy.

Called from POST /api/v1/dashboard/sync-extasy (admin only).
"""

import csv
import io
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Attendee, TicketType

logger = logging.getLogger(__name__)

# ── Extasy config ──────────────────────────────────────────────────────────────
EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_BASE     = "https://api.b2b.extasy.com/operations/reports"
ORDERS_URL      = f"{EXTASY_BASE}/orders/{EXTASY_EVENT_ID}"
TICKETS_URL     = f"{EXTASY_BASE}/tickets/{EXTASY_EVENT_ID}"

# Only ingest orders with these statuses
PAID_STATUSES = {"PAID"}

# Skip internal test tickets
TEST_TICKET_NAMES = {"test ticket", "test ticket card"}

# Extasy ticket name → our TicketType enum
TICKET_TYPE_MAP: dict[str, str] = {
    "investor pass":                    "vip",
    "vip pass":                         "vip",
    "vip black pass":                   "vip",
    "general pass":                     "delegate",
    "startup pass (application based)": "delegate",
    "startup pass":                     "delegate",
    "speaker pass":                     "speaker",
    "sponsor pass":                     "sponsor",
}

# Domains we won't use to infer company name
GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "protonmail.com", "me.com",
}

# Ticket tier order for upgrade logic
TIER_ORDER = ["delegate", "speaker", "sponsor", "vip"]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _fetch_csv(url: str) -> list[dict]:
    """Fetch an Extasy report endpoint and parse it as CSV."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.content.decode("iso-8859-1", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]


def _map_ticket_type(ticket_name: str) -> TicketType:
    key = ticket_name.lower().strip()
    mapped = TICKET_TYPE_MAP.get(key, "delegate")
    return TicketType(mapped)


def _infer_company(email: str) -> tuple[str, str]:
    """Return (company_name, company_website) inferred from email domain."""
    if "@" not in email:
        return "", ""
    domain = email.split("@")[1].lower()
    if domain in GENERIC_EMAIL_DOMAINS:
        return "", ""
    company = domain.replace("www.", "").split(".")[0].replace("-", " ").title()
    return company, f"https://{domain}"


def _tier_index(ticket_type: TicketType) -> int:
    try:
        return TIER_ORDER.index(ticket_type.value)
    except ValueError:
        return 0


# ── Main sync function ─────────────────────────────────────────────────────────

async def sync_extasy_to_db(db: AsyncSession) -> dict:
    """
    Pull PAID orders from Extasy and upsert into the attendees table.

    Returns a dict with sync stats:
        total_fetched, paid_count, inserted, upgraded, skipped, errors
    """
    logger.info("extasy_sync: fetching orders from %s", ORDERS_URL)

    try:
        orders = await _fetch_csv(ORDERS_URL)
    except Exception as exc:
        logger.error("extasy_sync: failed to fetch orders: %s", exc)
        raise RuntimeError(f"Failed to reach Extasy API: {exc}") from exc

    total_fetched = len(orders)
    paid_orders = [o for o in orders if o.get("status") in PAID_STATUSES]

    inserted      = 0
    upgraded      = 0
    skipped       = 0
    errors        = 0
    inserted_ids: list[str] = []
    seen_emails: set[str] = set()

    for order in paid_orders:
        try:
            ticket_name = (order.get("ticketNames") or "").split(",")[0].strip()

            # Skip test/internal tickets
            if ticket_name.lower().strip() in TEST_TICKET_NAMES:
                continue

            email = (order.get("email") or "").strip().lower()
            if not email:
                continue

            # Deduplicate within this batch — keep highest tier
            if email in seen_emails:
                continue
            seen_emails.add(email)

            first = (order.get("firstName") or "").strip()
            last  = (order.get("lastName")  or "").strip()
            name  = f"{first} {last}".strip() or "Unknown"

            ticket_type              = _map_ticket_type(ticket_name)
            company, company_website = _infer_company(email)

            enriched_profile = {
                "source":          "extasy",
                "extasy_order_id": order.get("id"),
                "ticket_code":     (order.get("ticketCodes") or "").split(",")[0].strip(),
                "ticket_name":     ticket_name,
                "phone":           order.get("phoneNumber") or None,
                "city":            order.get("city") or None,
                "country":         order.get("countryIso3Code") or None,
                "synced_at":       datetime.now(timezone.utc).isoformat(),
            }

            # Upsert by email
            result   = await db.execute(select(Attendee).where(Attendee.email == email))
            existing = result.scalar_one_or_none()

            if existing:
                # Upgrade ticket type if the new one is higher tier
                if _tier_index(ticket_type) > _tier_index(existing.ticket_type):
                    existing.ticket_type = ticket_type
                    existing.updated_at  = datetime.utcnow()
                    # Merge enriched_profile so we don't overwrite existing enrichment
                    merged = {**enriched_profile, **(existing.enriched_profile or {})}
                    existing.enriched_profile = merged
                    upgraded += 1
                else:
                    skipped += 1
            else:
                attendee = Attendee(
                    name=name,
                    email=email,
                    company=company,
                    title="",
                    ticket_type=ticket_type,
                    interests=[],
                    goals=None,
                    company_website=company_website or None,
                    enriched_profile=enriched_profile,
                )
                db.add(attendee)
                await db.flush()   # get the auto-assigned UUID
                inserted_ids.append(str(attendee.id))
                inserted += 1

        except Exception as exc:
            logger.error("extasy_sync: error processing order %s: %s", order.get("id"), exc)
            errors += 1
            continue

    await db.commit()

    result_stats = {
        "total_fetched":  total_fetched,
        "paid_count":     len(paid_orders),
        "inserted":       inserted,
        "upgraded":       upgraded,
        "skipped":        skipped,
        "errors":         errors,
        "inserted_ids":   inserted_ids,
    }
    logger.info("extasy_sync: complete %s", {k: v for k, v in result_stats.items() if k != "inserted_ids"})
    return result_stats


# ── Sync + Enrich pipeline ─────────────────────────────────────────────────────

async def sync_and_enrich() -> dict:
    """
    Daily pipeline:
      1. Pull PAID orders from Extasy → upsert into DB
      2. Enrich + embed only the newly inserted attendees
      3. Return combined stats

    Designed to be called from the APScheduler background job or the admin endpoint.
    """
    from app.core.database import async_session
    from app.models.attendee import Attendee as AttendeeModel
    from app.services.enrichment import EnrichmentService
    from app.services.embeddings import generate_ai_summary, embed_attendee, classify_intents
    from datetime import datetime

    logger.info("sync_and_enrich: starting daily pipeline")

    async with async_session() as db:
        sync_stats = await sync_extasy_to_db(db)

    new_ids = sync_stats.get("inserted_ids", [])
    enriched_ok = 0
    enriched_errors = 0

    if new_ids:
        logger.info("sync_and_enrich: enriching %d new attendees", len(new_ids))
        service = EnrichmentService()
        try:
            for attendee_id in new_ids:
                try:
                    async with async_session() as db:
                        attendee = await db.get(AttendeeModel, attendee_id)
                        if not attendee:
                            continue
                        enriched = await service.enrich_attendee(attendee)
                        attendee.enriched_profile = enriched
                        attendee.enriched_at = datetime.utcnow()
                        attendee.ai_summary = await generate_ai_summary(attendee)
                        attendee.intent_tags = await classify_intents(attendee)
                        attendee.embedding = await embed_attendee(attendee)
                        await db.commit()
                    enriched_ok += 1
                except Exception as exc:
                    logger.error("sync_and_enrich: enrich failed for %s: %s", attendee_id, exc)
                    enriched_errors += 1
        finally:
            await service.close()
    else:
        logger.info("sync_and_enrich: no new attendees to enrich")

    result = {
        **{k: v for k, v in sync_stats.items() if k != "inserted_ids"},
        "enriched_ok":     enriched_ok,
        "enriched_errors": enriched_errors,
    }
    logger.info("sync_and_enrich: pipeline complete %s", result)
    return result
