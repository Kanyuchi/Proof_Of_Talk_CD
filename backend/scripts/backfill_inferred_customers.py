"""
Backfill inferred_customer_profile for all attendees missing one.

Runs the same `infer_customer_profile()` GPT-4o call that the live enrichment
pipeline uses, then optionally re-embeds so the new ICP is reflected in the
attendee's vector. Re-running matches afterwards is recommended.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/backfill_inferred_customers.py            # only missing
    python scripts/backfill_inferred_customers.py --force    # all attendees
    python scripts/backfill_inferred_customers.py --dry-run  # no writes
    python scripts/backfill_inferred_customers.py --no-reembed
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from backend/ root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import async_session
from app.models.attendee import Attendee
from app.services.embeddings import infer_customer_profile, embed_attendee


async def main(force: bool, dry_run: bool, reembed: bool) -> None:
    async with async_session() as db:
        result = await db.execute(select(Attendee))
        attendees = result.scalars().all()

        targets = [
            a for a in attendees
            if force or not (a.inferred_customer_profile or {}).get("ideal_customers")
        ]
        print(f"Total attendees: {len(attendees)}")
        print(f"To process: {len(targets)} (force={force})")

        success = 0
        failed = 0
        for i, attendee in enumerate(targets, start=1):
            label = f"[{i}/{len(targets)}] {attendee.name} @ {attendee.company}"
            try:
                icp = await infer_customer_profile(attendee)
                if not icp.get("ideal_customers"):
                    print(f"  ⚠️  {label} — empty ICP returned")
                    failed += 1
                    continue
                personas = len(icp.get("ideal_customers") or [])
                print(f"  ✓ {label} — {personas} customer personas")

                if dry_run:
                    continue

                attendee.inferred_customer_profile = icp
                if reembed:
                    attendee.embedding = await embed_attendee(attendee)
                db.add(attendee)
                await db.commit()
                success += 1
            except Exception as e:
                print(f"  ✗ {label} — {e}")
                failed += 1
                await db.rollback()

        print(f"\nDone. success={success} failed={failed} dry_run={dry_run}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-infer even if ICP already exists")
    parser.add_argument("--dry-run", action="store_true", help="Print but do not save")
    parser.add_argument("--no-reembed", action="store_true", help="Skip re-embedding after ICP update")
    args = parser.parse_args()
    asyncio.run(main(force=args.force, dry_run=args.dry_run, reembed=not args.no_reembed))
