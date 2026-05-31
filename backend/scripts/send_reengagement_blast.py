#!/usr/bin/env python3
"""Operator-driven re-engagement blast to unregistered ticket-holders.

Spec: docs/superpowers/specs/2026-05-31-reengagement-blast-design.md
Plan: docs/superpowers/plans/2026-05-31-reengagement-blast-plan.md

Run from `backend/` with venv active and `.env` loaded:

    # PREVIEW (default - sends nothing)
    python scripts/send_reengagement_blast.py

    # Print cohort breakdown only
    python scripts/send_reengagement_blast.py --status

    # Smoke-send to a single recipient
    python scripts/send_reengagement_blast.py --only you@xyz.com --confirm

    # Bounded wave
    python scripts/send_reengagement_blast.py --limit 50 --confirm

    # Full blast (skips anyone in the ledger)
    python scripts/send_reengagement_blast.py --confirm

Idempotent via `backend/exports/reengagement_sent.log`. Cohort sorted by
descending incoming-interest-count then total-matches so the highest-
leverage recipients send first if a wave is capped.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `app.*` importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.core.database import async_session  # noqa: E402
from app.services.email import send_reengagement_email  # noqa: E402
from app.services.reengagement_blast import (  # noqa: E402
    RecipientContext,
    build_cohort,
    fill_top_matches,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reengagement_blast")

LEDGER = Path(__file__).resolve().parent.parent / "exports" / "reengagement_sent.log"


def load_ledger() -> set[str]:
    if not LEDGER.exists():
        return set()
    return {
        line.split("\t", 1)[0].strip().lower()
        for line in LEDGER.read_text().splitlines()
        if line.strip()
    }


def append_ledger(email_addr: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(f"{email_addr}\t{datetime.now(timezone.utc).isoformat()}\n")


async def gather_cohort(only: str | None) -> list[RecipientContext]:
    async with async_session() as db:
        cohort = await build_cohort(db)
        if only:
            cohort = [c for c in cohort if c.email.lower() == only.lower()]
        cohort.sort(
            key=lambda c: (c.incoming_interest_count, c.total_matches),
            reverse=True,
        )
        for c in cohort:
            await fill_top_matches(db, c)
    return cohort


def _filter_sendable(
    cohort: list[RecipientContext], already_sent: set[str]
) -> list[RecipientContext]:
    out: list[RecipientContext] = []
    for c in cohort:
        if c.email.lower() in already_sent:
            continue
        if c.total_matches == 0 or not c.top_matches:
            continue
        out.append(c)
    return out


def cmd_status(cohort: list[RecipientContext], already_sent: set[str]) -> None:
    sendable = _filter_sendable(cohort, already_sent)
    skipped_no_match = sum(1 for c in cohort if c.total_matches == 0 or not c.top_matches)
    skipped_already_sent = len(cohort) - len(sendable) - skipped_no_match
    print(f"Cohort size:               {len(cohort)}")
    print(f"Already in ledger:         {skipped_already_sent}")
    print(f"No matches (skip):         {skipped_no_match}")
    print(f"Sendable now:              {len(sendable)}")
    by_incoming = sum(1 for c in sendable if c.incoming_interest_count > 0)
    print(f"  with incoming interest:  {by_incoming}")
    print(f"  match-count anchor only: {len(sendable) - by_incoming}")


def cmd_preview(
    cohort: list[RecipientContext], already_sent: set[str], limit: int | None
) -> None:
    sendable = _filter_sendable(cohort, already_sent)
    if limit:
        sendable = sendable[:limit]
    print(f"PREVIEW: would send to {len(sendable)} recipients")
    print(f"Ledger: {LEDGER}")
    print("First 5:")
    for c in sendable[:5]:
        top1 = c.top_matches[0]["name"] if c.top_matches else "NONE"
        print(
            f"  {c.email:40s} matches={c.total_matches:3d} incoming={c.incoming_interest_count:2d}"
            f" top1={top1[:30]}"
        )
    print("\nRe-run with --confirm to actually send.")


def cmd_confirm(
    cohort: list[RecipientContext], already_sent: set[str], limit: int | None
) -> None:
    sendable = _filter_sendable(cohort, already_sent)
    if limit:
        sendable = sendable[:limit]
    log.info("Sending to %d recipients", len(sendable))
    sent = errors = 0
    BAIL_AFTER = 100
    BAIL_RATE = 0.05
    for i, c in enumerate(sendable, 1):
        ok = send_reengagement_email(
            to_email=c.email,
            attendee_name=c.first_name,
            first_name=c.first_name,
            total_matches=c.total_matches,
            incoming_interest_count=c.incoming_interest_count,
            top_matches=c.top_matches,
            magic_token=c.magic_token,
            force=True,
        )
        if ok:
            sent += 1
            append_ledger(c.email)
        else:
            errors += 1
        if i % 25 == 0:
            log.info(
                "Progress: %d/%d sent=%d errors=%d", i, len(sendable), sent, errors
            )
        if i == BAIL_AFTER and errors / BAIL_AFTER > BAIL_RATE:
            log.error(
                "Bail: %d errors in first %d sends (>%.0f%%)",
                errors,
                BAIL_AFTER,
                BAIL_RATE * 100,
            )
            break
    log.info("DONE: sent=%d errors=%d", sent, errors)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--confirm", action="store_true", help="actually send (default: preview)"
    )
    ap.add_argument("--limit", type=int, default=None, help="wave cap")
    ap.add_argument("--only", type=str, default=None, help="single recipient smoke")
    ap.add_argument(
        "--status", action="store_true", help="print cohort breakdown and exit"
    )
    args = ap.parse_args()

    cohort = asyncio.run(gather_cohort(args.only))
    already_sent = load_ledger()

    if args.status:
        cmd_status(cohort, already_sent)
        return 0
    if args.confirm:
        cmd_confirm(cohort, already_sent, args.limit)
        return 0
    cmd_preview(cohort, already_sent, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
