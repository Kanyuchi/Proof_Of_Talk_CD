"""
One-shot backfill for Rhuna pass names on existing attendees.

Background
----------
Until 2026-05-16 the Extasy sync collapsed Rhuna's granular pass names
(General / Startup / Press / Investor / VIP / VIP Black / Speaker / Sponsor)
into the 4-value TicketType enum (DELEGATE / SPEAKER / VIP / SPONSOR).
The raw name was stashed at top-level `enriched_profile.ticket_name`
(via `extasy_sync.py`) or in the standalone `extasy_ticket_name` column
(via `ingest_extasy.py`), but nothing read it.

The fix moves the granular name to `enriched_profile.extasy.ticket_name`
(nested namespace, JSONB → no migration). This script backfills the
existing Rhuna attendees in place.

For each row with `extasy_order_id IS NOT NULL`:
  1. Build a fresh `extasy` sub-dict from whatever Rhuna-authoritative
     data we already have (top-level enriched_profile fields, then the
     `extasy_ticket_name`/`extasy_ticket_code` columns as fallback).
  2. Set `enriched_profile["extasy"] = <new block>`.
  3. Strip the old top-level keys (ticket_name, ticket_code, phone, city,
     country, paid_amount, voucher_code, synced_at, extasy_order_id) from
     enriched_profile — they're either canonical columns or live inside
     `.extasy` now.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/backfill_rhuna_pass_names.py --dry-run
    python scripts/backfill_rhuna_pass_names.py
"""
import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import or_, select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import async_session
from app.models.attendee import Attendee


# Top-level enriched_profile keys that the old extasy_sync wrote and that
# now belong under .extasy. Removed from the top level so we don't keep
# two sources of truth.
LEGACY_TOPLEVEL_KEYS = [
    "ticket_name",
    "ticket_code",
    "phone",
    "city",
    "country",
    "paid_amount",
    "voucher_code",
    "synced_at",
    "extasy_order_id",
]


def _build_extasy_block(attendee: Attendee) -> tuple[dict, str]:
    """Return (extasy_block, source_label).

    source_label is one of:
      - "nested"      — already migrated, just normalising
      - "toplevel"    — copied from enriched_profile.ticket_name etc.
      - "column"      — copied from the extasy_ticket_name column
      - "unknown"     — Rhuna order but we have no pass name on file
    """
    ep = dict(attendee.enriched_profile or {})

    existing_nested = ep.get("extasy") or {}
    if isinstance(existing_nested, dict) and existing_nested.get("ticket_name"):
        return existing_nested, "nested"

    toplevel_name = ep.get("ticket_name")
    if toplevel_name:
        return {
            "order_id":     attendee.extasy_order_id or ep.get("extasy_order_id"),
            "ticket_code":  ep.get("ticket_code")
                              or getattr(attendee, "extasy_ticket_code", None),
            "ticket_name":  toplevel_name,
            "phone":        ep.get("phone")
                              or getattr(attendee, "phone_number", None),
            "city":         ep.get("city")
                              or getattr(attendee, "city", None),
            "country":      ep.get("country") or attendee.country_iso3,
            "paid_amount":  ep.get("paid_amount"),
            "voucher_code": ep.get("voucher_code"),
            "synced_at":    ep.get("synced_at"),
        }, "toplevel"

    column_name = getattr(attendee, "extasy_ticket_name", None)
    if column_name:
        return {
            "order_id":     attendee.extasy_order_id,
            "ticket_code":  getattr(attendee, "extasy_ticket_code", None),
            "ticket_name":  column_name,
            "phone":        getattr(attendee, "phone_number", None),
            "city":         getattr(attendee, "city", None),
            "country":      attendee.country_iso3,
            "paid_amount":  None,
            "voucher_code": None,
            "synced_at":    None,
        }, "column"

    return {
        "order_id":     attendee.extasy_order_id,
        "ticket_code":  None,
        "ticket_name":  None,
        "phone":        None,
        "city":         None,
        "country":      attendee.country_iso3,
        "paid_amount":  None,
        "voucher_code": None,
        "synced_at":    None,
    }, "unknown"


async def main(dry_run: bool) -> None:
    async with async_session() as db:
        # Catch rows where the column is set (normal Extasy path) AND rows
        # where only the JSONB carries the order_id (Runa webhook / older
        # ingest paths that never populated the column).
        result = await db.execute(
            select(Attendee).where(
                or_(
                    Attendee.extasy_order_id.is_not(None),
                    Attendee.enriched_profile["extasy_order_id"].as_string().is_not(None),
                    Attendee.enriched_profile["ticket_name"].as_string().is_not(None),
                )
            )
        )
        attendees = result.scalars().all()

    print(f"Found {len(attendees)} attendees with Rhuna ticket data")
    if dry_run:
        print("DRY-RUN: no writes will be made\n")

    source_counts: Counter[str] = Counter()
    pass_counts: Counter[str] = Counter()
    rewritten = 0
    unchanged = 0

    async with async_session() as db:
        for attendee in attendees:
            # Re-fetch within the write session so SQLAlchemy tracks changes.
            row = await db.get(Attendee, attendee.id)
            if row is None:
                continue

            block, source = _build_extasy_block(row)
            source_counts[source] += 1
            if block.get("ticket_name"):
                pass_counts[block["ticket_name"]] += 1

            ep = dict(row.enriched_profile or {})
            new_ep = {k: v for k, v in ep.items() if k not in LEGACY_TOPLEVEL_KEYS}
            new_ep["extasy"] = block
            new_ep.setdefault("source", "extasy")

            if new_ep == (row.enriched_profile or {}):
                unchanged += 1
                continue

            rewritten += 1
            if not dry_run:
                row.enriched_profile = new_ep
                # JSONB mutations in place are not auto-detected by SQLA;
                # reassigning the dict above is enough, but flag for safety.
                flag_modified(row, "enriched_profile")

        if not dry_run:
            await db.commit()

    print(f"\nRewrites: {rewritten}   Unchanged: {unchanged}")
    print("Source breakdown:")
    for src, n in source_counts.most_common():
        print(f"  {src:<10} {n}")
    print("\nPass-name distribution after backfill:")
    for name, n in pass_counts.most_common():
        print(f"  {n:>4}  {name}")
    missing = source_counts.get("unknown", 0)
    if missing:
        print(
            f"\n⚠️  {missing} attendees with no pass name on file. "
            "Re-run extasy_sync once deployed to pick up the rest."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="No writes; print plan")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
