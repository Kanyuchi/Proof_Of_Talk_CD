"""
Extasy → RDS sync service
=========================
Fetches valid orders (PAID + REDEEMED) from the Extasy ticketing API and
upserts them into the PostgreSQL database via SQLAlchemy.

Called from POST /api/v1/dashboard/sync-extasy (admin only).
"""

import csv
import io
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError, InterfaceError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Attendee, TicketType

logger = logging.getLogger(__name__)

# ── Extasy config ──────────────────────────────────────────────────────────────
EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_BASE     = "https://api.b2b.extasy.com/operations/reports"
ORDERS_URL      = f"{EXTASY_BASE}/orders/{EXTASY_EVENT_ID}"
TICKETS_URL     = f"{EXTASY_BASE}/tickets/{EXTASY_EVENT_ID}"

# Only ingest orders with these statuses (includes complimentary/voucher tickets)
VALID_STATUSES = {"PAID", "REDEEMED"}

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


def _parse_extasy_dt(s: str | None) -> datetime | None:
    """Parse Extasy `createdAtUtc` (e.g. '2026-02-12 15:52:44.692113') to a
    UTC-aware datetime suitable for the `ticket_bought_at` timestamptz column.
    """
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace(" ", "T")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ── Main sync function ─────────────────────────────────────────────────────────

async def sync_extasy_to_db() -> dict:
    """
    Pull valid orders (PAID + REDEEMED) from Extasy and upsert into the
    attendees table.

    Processes orders in CHUNK_SIZE batches, each in its own SQLAlchemy session.
    If a chunk's connection drops mid-batch (Supabase pooler reset, network
    blip, idle-timeout), only that chunk is lost — the next chunk opens a
    fresh session and continues. This is what protects us from the Apr 28 /
    May 5-6 silent-failure pattern where one connection drop poisoned the
    rest of the loop with cascading "Can't reconnect until invalid
    transaction is rolled back" errors.

    Returns a dict with sync stats:
        total_fetched, valid_count, inserted, upgraded, skipped, errors
    """
    from app.core.database import async_session

    logger.info("extasy_sync: fetching orders from %s", ORDERS_URL)

    try:
        orders = await _fetch_csv(ORDERS_URL)
    except Exception as exc:
        logger.error("extasy_sync: failed to fetch orders: %s", exc)
        raise RuntimeError(f"Failed to reach Extasy API: {exc}") from exc

    total_fetched = len(orders)
    valid_orders = [o for o in orders if o.get("status") in VALID_STATUSES]

    inserted      = 0
    upgraded      = 0
    backfilled    = 0
    skipped       = 0
    errors        = 0
    chunks_failed = 0
    inserted_ids: list[str] = []
    seen_emails: set[str] = set()

    # Chunk size of 30: small enough that a pooler drop loses ≤30 rows of
    # progress, large enough that session-create overhead stays in the noise.
    CHUNK_SIZE = 30

    for chunk_start in range(0, len(valid_orders), CHUNK_SIZE):
        chunk = valid_orders[chunk_start:chunk_start + CHUNK_SIZE]
        try:
            async with async_session() as db:
                chunk_stats = await _process_order_chunk(
                    db, chunk, seen_emails, inserted_ids,
                )
                inserted   += chunk_stats["inserted"]
                upgraded   += chunk_stats["upgraded"]
                backfilled += chunk_stats["backfilled"]
                skipped    += chunk_stats["skipped"]
                errors     += chunk_stats["errors"]
                await db.commit()
        except (DBAPIError, OperationalError, InterfaceError) as exc:
            # Connection-level failure (pooler drop, server reset, asyncpg
            # ConnectionDoesNotExistError, etc). Lose this chunk, keep going
            # with a fresh session for the next one.
            chunks_failed += 1
            errors += len(chunk)
            logger.error(
                "extasy_sync: chunk %d-%d failed on connection error, will continue with fresh session: %s",
                chunk_start, chunk_start + len(chunk) - 1, exc,
            )
        except Exception as exc:
            chunks_failed += 1
            errors += len(chunk)
            logger.error(
                "extasy_sync: chunk %d-%d unexpected failure: %s",
                chunk_start, chunk_start + len(chunk) - 1, exc,
            )

    return {
        "total_fetched":  total_fetched,
        "valid_count":    len(valid_orders),
        "inserted":       inserted,
        "upgraded":       upgraded,
        "backfilled":     backfilled,
        "skipped":        skipped,
        "errors":         errors,
        "chunks_failed":  chunks_failed,
        "inserted_ids":   inserted_ids,
    }


async def _process_order_chunk(
    db: AsyncSession,
    chunk: list[dict],
    seen_emails: set[str],
    inserted_ids: list[str],
) -> dict:
    """Process one chunk of orders within a single session. Per-row
    SAVEPOINTs continue to isolate per-row data errors as before."""
    inserted = upgraded = backfilled = skipped = errors = 0

    for order in chunk:
        order_id    = order.get("id")
        ticket_name = (order.get("ticketNames") or "").split(",")[0].strip()

        # Skip test/internal tickets
        if ticket_name.lower().strip() in TEST_TICKET_NAMES:
            continue

        email = (order.get("email") or "").strip().lower()
        if not email:
            continue

        # Deduplicate within this batch — keep first occurrence
        if email in seen_emails:
            continue
        seen_emails.add(email)

        first = (order.get("firstName") or "").strip()
        last  = (order.get("lastName")  or "").strip()
        name  = f"{first} {last}".strip() or "Unknown"

        ticket_type              = _map_ticket_type(ticket_name)
        company, company_website = _infer_company(email)
        country_iso3             = order.get("countryIso3Code") or None
        ticket_bought_at         = _parse_extasy_dt(order.get("createdAtUtc"))

        enriched_profile = {
            "source":          "extasy",
            "extasy_order_id": order_id,
            "ticket_code":     (order.get("ticketCodes") or "").split(",")[0].strip(),
            "ticket_name":     ticket_name,
            "phone":           order.get("phoneNumber") or None,
            "city":            order.get("city") or None,
            "country":         country_iso3,
            "paid_amount":     order.get("paymentsAmount") or None,
            "voucher_code":    order.get("voucherCode") or None,
            "synced_at":       datetime.now(timezone.utc).isoformat(),
        }

        # Per-row savepoint isolates failures so one bad row can't poison the
        # whole batch (previous behavior caused 100+ cascading "session has been
        # rolled back" errors after a single IntegrityError).
        try:
            async with db.begin_nested():
                result   = await db.execute(select(Attendee).where(Attendee.email == email))
                existing = result.scalar_one_or_none()

                if existing:
                    changed = False

                    # Backfill the ticket-holder linkage if this attendee
                    # entered via another path (speaker sync, nomination, etc.)
                    # and we never recorded their Rhuna order.
                    if not getattr(existing, "extasy_order_id", None):
                        existing.extasy_order_id = order_id
                        changed = True
                    if not getattr(existing, "country_iso3", None) and country_iso3:
                        existing.country_iso3 = country_iso3
                        changed = True
                    if not getattr(existing, "ticket_bought_at", None) and ticket_bought_at:
                        existing.ticket_bought_at = ticket_bought_at
                        changed = True

                    # Merge Extasy fields into enriched_profile without
                    # clobbering anything already there (existing data wins).
                    merged = {**enriched_profile, **(existing.enriched_profile or {})}
                    if merged != (existing.enriched_profile or {}):
                        existing.enriched_profile = merged
                        changed = True

                    # Upgrade ticket type only if the new one is higher tier
                    upgraded_tier = False
                    if _tier_index(ticket_type) > _tier_index(existing.ticket_type):
                        existing.ticket_type = ticket_type
                        upgraded_tier = True
                        changed = True

                    if changed:
                        existing.updated_at = datetime.utcnow()
                        await db.flush()
                        if upgraded_tier:
                            upgraded += 1
                        else:
                            backfilled += 1
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
                    # Top-level columns that aren't on the ORM class but exist
                    # in the schema (added via Alembic). Set via __dict__ so
                    # SQLAlchemy passes them through on INSERT.
                    if country_iso3:
                        attendee.country_iso3 = country_iso3
                    attendee.extasy_order_id = order_id
                    if ticket_bought_at:
                        attendee.ticket_bought_at = ticket_bought_at
                    db.add(attendee)
                    await db.flush()   # get the auto-assigned UUID
                    inserted_ids.append(str(attendee.id))
                    inserted += 1
        except IntegrityError as exc:
            # Rare race: SELECT didn't find the row but INSERT hit the unique
            # index. Savepoint already rolled back; outer transaction is healthy.
            # Next sync run will SELECT successfully and update normally.
            logger.warning(
                "extasy_sync: integrity conflict on order %s (email=%s) — savepoint rolled back, will reconcile next run: %s",
                order_id, email, exc,
            )
            errors += 1
        except Exception as exc:
            logger.error("extasy_sync: error processing order %s: %s", order_id, exc)
            errors += 1

    return {
        "inserted":   inserted,
        "upgraded":   upgraded,
        "backfilled": backfilled,
        "skipped":    skipped,
        "errors":     errors,
    }


# ── Sync + Enrich pipeline ─────────────────────────────────────────────────────

async def sync_and_enrich() -> dict:
    """
    Daily pipeline:
      1. Pull valid orders (PAID + REDEEMED) from Extasy → upsert into DB
      2. Enrich + embed only the newly inserted attendees
      3. Return combined stats

    Designed to be called from the APScheduler background job or the admin endpoint.
    """
    from app.core.database import async_session
    from app.models.attendee import Attendee as AttendeeModel
    from app.services.enrichment import EnrichmentService
    from app.services.embeddings import generate_ai_summary, embed_attendee, classify_intents, classify_verticals
    from datetime import datetime

    logger.info("sync_and_enrich: starting daily pipeline")

    # sync_extasy_to_db now manages its own per-chunk sessions internally so
    # one connection drop can't poison the whole batch.
    sync_stats = await sync_extasy_to_db()

    new_ids = sync_stats.get("inserted_ids", [])
    logger.info(
        "sync_and_enrich: extasy stats — fetched=%d valid=%d inserted=%d upgraded=%d backfilled=%d skipped=%d errors=%d chunks_failed=%d",
        sync_stats.get("total_fetched", 0), sync_stats.get("valid_count", 0),
        sync_stats.get("inserted", 0), sync_stats.get("upgraded", 0),
        sync_stats.get("backfilled", 0), sync_stats.get("skipped", 0),
        sync_stats.get("errors", 0), sync_stats.get("chunks_failed", 0),
    )
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
                        attendee.vertical_tags = await classify_verticals(attendee)
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
