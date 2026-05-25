"""
Extasy check-ins → DB sync
==========================
The Extasy `checkins` report is **per-attendee**: when an individual claims /
personalizes their pass, a check-in record is created carrying that real
holder's own email, name, company, and job title. The buyer-keyed `orders` /
`tickets` feed (see ``extasy_sync``) can only ever see the purchaser, so a
multi-pass order collapses to one person and passes bought without a per-attendee
email never become a profile.

This sync ingests the check-ins feed to recover those people: it inserts the
claimants we don't have yet and backfills (existing-wins) the ones we do, using
the richer per-attendee company/title. Pass type — absent from the check-ins
feed — is recovered by joining each check-in back to its order (by order number,
refined by QR code).

Shares all heavy lifting with ``extasy_sync`` (fetch, helpers, heartbeat,
connection-error taxonomy) to stay consistent with that hard-won path.

Called from POST /api/v1/dashboard/sync-checkins (admin) and the 02:05 UTC cron.
"""

import asyncio
import logging
import secrets
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Attendee
from app.services.extasy_sync import (
    EXTASY_BASE,
    EXTASY_EVENT_ID,
    ORDERS_URL,
    TEST_BUYER_NAME_PATTERNS,
    _CONNECTION_ERRORS,
    _fetch_csv,
    _infer_company,
    _map_ticket_type,
    _parse_extasy_dt,
    _record_sync_status,
    _tier_index,
)

logger = logging.getLogger(__name__)

CHECKINS_URL = f"{EXTASY_BASE}/checkins/{EXTASY_EVENT_ID}"


# ── Pass-type resolver (join check-in → order) ───────────────────────────────

def _build_order_maps(orders: list[dict]) -> tuple[dict, dict]:
    """Index the orders feed for pass-type lookup.

    Returns (order_pass, order_names):
      - order_pass[orderNumber]  = {qrCode: ticketName}  (positional zip; only
        populated when QR and ticket-name counts line up)
      - order_names[orderNumber] = [ticketName, ...]      (for fallback)
    """
    order_pass: dict[str, dict[str, str]] = {}
    order_names: dict[str, list[str]] = {}
    for o in orders:
        onum = (o.get("orderNumber") or "").strip()
        if not onum:
            continue
        names = [n.strip() for n in (o.get("ticketNames") or "").split(",") if n.strip()]
        qrs = [q.strip() for q in (o.get("qrCodes") or "").split(",") if q.strip()]
        order_names[onum] = names
        order_pass[onum] = dict(zip(qrs, names)) if len(qrs) == len(names) else {}
    return order_pass, order_names


def _resolve_pass(checkin: dict, order_pass: dict, order_names: dict) -> str | None:
    """Resolve the pass name for a check-in: exact QR match first, then the
    order's first ticket name, else None (caller maps None → DELEGATE)."""
    onum = (checkin.get("displayableOrderNumber") or "").strip()
    qr = (checkin.get("qrCode") or "").strip()
    by_qr = order_pass.get(onum)
    if by_qr and qr in by_qr:
        return by_qr[qr]
    names = order_names.get(onum)
    if names:
        return names[0]
    return None


# ── Per-row upsert ───────────────────────────────────────────────────────────

async def _process_checkin_chunk(
    db: AsyncSession,
    chunk: list[dict],
    order_pass: dict,
    order_names: dict,
    seen_emails: set[str],
    inserted_ids: list[str],
    error_reasons: Counter | None = None,
) -> dict:
    """Upsert a batch of check-in rows. Existing-wins: backfill only blank
    fields, upgrade ticket type upward only, overwrite the `.checkin` block.
    Each row runs in its own savepoint so one bad row can't poison the batch;
    connection-drop errors propagate so the caller can retry on a fresh session.
    """
    if error_reasons is None:
        error_reasons = Counter()

    inserted = upgraded = backfilled = skipped = errors = 0

    for ck in chunk:
        first = (ck.get("firstName") or "").strip()
        last = (ck.get("lastName") or "").strip()
        name = f"{first} {last}".strip() or "Unknown"

        # Skip QA / internal testers (same patterns as extasy_sync).
        if any(p in name.lower() for p in TEST_BUYER_NAME_PATTERNS):
            continue

        email = (ck.get("email") or "").strip().lower()
        if not email:
            continue

        # Deduplicate within this batch — keep first occurrence.
        if email in seen_emails:
            continue
        seen_emails.add(email)

        pass_name = _resolve_pass(ck, order_pass, order_names)
        ticket_type = _map_ticket_type(pass_name or "")
        company = (ck.get("companyName") or "").strip()
        company_website = ""
        if not company:
            company, company_website = _infer_company(email)
        title = (ck.get("jobTitle") or "").strip()
        country_iso3 = (ck.get("countryIso3Code") or "").strip() or None
        ticket_bought_at = _parse_extasy_dt(ck.get("createdAt"))

        checkin_block = {
            "checkin_id":   ck.get("checkinId"),
            "order_number": (ck.get("displayableOrderNumber") or "").strip() or None,
            "qr_code":      (ck.get("qrCode") or "").strip() or None,
            "ticket_name":  pass_name,
            "phone":        ck.get("phone") or None,
            "city":         ck.get("city") or None,
            "country":      country_iso3,
            "full_price":   ck.get("fullPrice") or None,
            "synced_at":    datetime.now(timezone.utc).isoformat(),
        }
        enriched_profile = {"source": "checkin", "checkin": checkin_block}

        try:
            async with db.begin_nested():
                result = await db.execute(select(Attendee).where(Attendee.email == email))
                existing = result.scalar_one_or_none()

                if existing:
                    changed = False

                    # Backfill only blank per-attendee fields — never overwrite.
                    if not (existing.company or "").strip() and company:
                        existing.company = company
                        changed = True
                    if not (existing.title or "").strip() and title:
                        existing.title = title
                        changed = True
                    if not getattr(existing, "country_iso3", None) and country_iso3:
                        existing.country_iso3 = country_iso3
                        changed = True
                    if not getattr(existing, "ticket_bought_at", None) and ticket_bought_at:
                        existing.ticket_bought_at = ticket_bought_at
                        changed = True

                    # Merge: existing-wins, except the `.checkin` sub-key which is
                    # the authoritative per-attendee snapshot, always refreshed.
                    current = dict(existing.enriched_profile or {})
                    merged = {**enriched_profile, **current}
                    merged["checkin"] = checkin_block
                    if merged != (existing.enriched_profile or {}):
                        existing.enriched_profile = merged
                        changed = True

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
                        title=title,
                        ticket_type=ticket_type,
                        interests=[],
                        goals=None,
                        company_website=company_website or None,
                        enriched_profile=enriched_profile,
                        magic_access_token=secrets.token_urlsafe(32),
                    )
                    if country_iso3:
                        attendee.country_iso3 = country_iso3
                    if ticket_bought_at:
                        attendee.ticket_bought_at = ticket_bought_at
                    db.add(attendee)
                    await db.flush()
                    inserted_ids.append(str(attendee.id))
                    inserted += 1
        except _CONNECTION_ERRORS:
            # Dead session — propagate so the chunk handler retries on a fresh
            # one. Must NOT be miscounted as a per-row data error.
            raise
        except IntegrityError as exc:
            logger.warning(
                "checkins_sync: integrity conflict (email=%s) — savepoint rolled "
                "back, will reconcile next run: %s", email, exc,
            )
            errors += 1
            error_reasons[f"IntegrityError: {str(exc).splitlines()[0][:120]}"] += 1
        except Exception as exc:
            logger.error("checkins_sync: error processing checkin (email=%s): %s", email, exc)
            errors += 1
            error_reasons[f"{type(exc).__name__}: {str(exc).splitlines()[0][:120]}"] += 1

    return {
        "inserted":   inserted,
        "upgraded":   upgraded,
        "backfilled": backfilled,
        "skipped":    skipped,
        "errors":     errors,
    }


# ── Orchestrator ─────────────────────────────────────────────────────────────

async def sync_checkins_to_db() -> dict:
    """Pull the check-ins feed (+ orders for the pass join) and upsert per-row in
    chunked sessions. Mirrors extasy_sync's chunk/retry resilience. Newly
    inserted attendees are sent through ``run_full_enrichment`` detached so they
    become matchable within minutes rather than waiting for the nightly sweep.
    """
    from app.core.database import async_session

    logger.info("checkins_sync: fetching %s", CHECKINS_URL)
    try:
        checkins = await _fetch_csv(CHECKINS_URL)
        orders = await _fetch_csv(ORDERS_URL)
    except Exception as exc:
        logger.error("checkins_sync: failed to fetch feeds: %s", exc)
        raise RuntimeError(f"Failed to reach Extasy API: {exc}") from exc

    order_pass, order_names = _build_order_maps(orders)

    total_fetched = len(checkins)
    inserted = upgraded = backfilled = skipped = errors = chunks_failed = 0
    inserted_ids: list[str] = []
    seen_emails: set[str] = set()
    error_reasons: Counter = Counter()
    CHUNK_SIZE = 30

    for chunk_start in range(0, len(checkins), CHUNK_SIZE):
        chunk = checkins[chunk_start:chunk_start + CHUNK_SIZE]
        chunk_label = f"{chunk_start}-{chunk_start + len(chunk) - 1}"
        succeeded = False
        last_conn_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                async with async_session() as db:
                    chunk_stats = await _process_checkin_chunk(
                        db, chunk, order_pass, order_names,
                        seen_emails, inserted_ids, error_reasons,
                    )
                    await db.commit()
                inserted   += chunk_stats["inserted"]
                upgraded   += chunk_stats["upgraded"]
                backfilled += chunk_stats["backfilled"]
                skipped    += chunk_stats["skipped"]
                errors     += chunk_stats["errors"]
                succeeded = True
                break
            except _CONNECTION_ERRORS as exc:
                last_conn_exc = exc
                logger.warning("checkins_sync: chunk %s connection drop on attempt %d/2: %s",
                               chunk_label, attempt, exc)
                continue
            except Exception as exc:
                chunks_failed += 1
                errors += len(chunk)
                error_reasons[f"chunk_failed/{type(exc).__name__}: {str(exc).splitlines()[0][:120]}"] += 1
                logger.error("checkins_sync: chunk %s unexpected failure: %s", chunk_label, exc)
                succeeded = True
                break

        if not succeeded:
            chunks_failed += 1
            errors += len(chunk)
            error_reasons[
                f"chunk_failed/{type(last_conn_exc).__name__}: {str(last_conn_exc).splitlines()[0][:120]}"
            ] += 1
            logger.error("checkins_sync: chunk %s failed after 2 connection-drop attempts: %s",
                         chunk_label, last_conn_exc)

    stats = {
        "total_fetched": total_fetched,
        "distinct":      len(seen_emails),
        "inserted":      inserted,
        "upgraded":      upgraded,
        "backfilled":    backfilled,
        "skipped":       skipped,
        "errors":        errors,
        "chunks_failed": chunks_failed,
        "error_reasons": dict(error_reasons),
        "inserted_ids":  inserted_ids,
    }

    overall_status = "ok" if chunks_failed == 0 else "partial"
    try:
        await _record_sync_status("checkins_sync", overall_status, stats)
    except Exception as exc:
        logger.warning("checkins_sync: failed to persist sync_status row: %s", exc)

    # Make freshly-recovered people matchable now (detached, best-effort).
    if inserted_ids:
        from app.services.profile_pipeline import run_full_enrichment
        for aid in inserted_ids:
            try:
                asyncio.create_task(run_full_enrichment(uuid.UUID(aid)))
            except Exception as exc:
                logger.warning("checkins_sync: could not schedule enrichment for %s: %s", aid, exc)

    logger.info(
        "checkins_sync: fetched=%d distinct=%d inserted=%d backfilled=%d upgraded=%d skipped=%d errors=%d",
        total_fetched, len(seen_emails), inserted, backfilled, upgraded, skipped, errors,
    )
    return stats
