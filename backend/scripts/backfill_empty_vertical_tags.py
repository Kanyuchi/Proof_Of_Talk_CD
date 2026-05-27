"""Backfill `vertical_tags` for attendees who arrived through paths other
than the extasy_sync / speakers_sync ingest (admin-created, sponsor-invite,
magic-link claim, manual seed). Diagnosed 2026-05-27: 663/1275 attendees
(52%, including 94 VIPs) had empty vertical_tags, which blocks the
COMPLEMENTARY_VERTICALS rerank boost in matching and routes investors to
other investors instead of LP/family-office complementary matches.

The systemic fix (added to `MatchingEngine.process_attendee` in the same
commit) ensures future re-embeds pick up the classifier. This script is
the one-off backfill for the historical rows.

For each target attendee:
  - Run `classify_verticals` (GPT-4o, ~$0.001/call)
  - Re-embed (the embedding text now includes the vertical_tags line)
  - Save
  - Skip match regeneration to keep cost bounded; matches refresh
    organically the next time the attendee saves their profile, OR via
    `--regen-matches` for a smaller targeted set (Desmond etc.)

Usage:
  python scripts/backfill_empty_vertical_tags.py                    # dry-run all empty
  python scripts/backfill_empty_vertical_tags.py --confirm          # commit all empty
  python scripts/backfill_empty_vertical_tags.py --vip-only --confirm  # just the 94 VIPs first
  python scripts/backfill_empty_vertical_tags.py --attendee-id <uuid> --confirm --regen-matches
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, or_, func  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Attendee  # noqa: E402
from app.services.embeddings import classify_verticals, embed_attendee  # noqa: E402


async def main(
    confirm: bool,
    vip_only: bool,
    attendee_id: str | None,
    regen_matches: bool,
    limit: int | None,
) -> None:
    async with async_session() as db:
        # Use array_length instead of == [] because the column is text[]
        # but SQLAlchemy parameterises empty list as varchar[], which
        # asyncpg rejects with operator does not exist.
        q = select(Attendee).where(
            or_(
                Attendee.vertical_tags.is_(None),
                func.coalesce(func.array_length(Attendee.vertical_tags, 1), 0) == 0,
            ),
        )
        if attendee_id:
            q = q.where(Attendee.id == attendee_id)
        elif vip_only:
            q = q.where(Attendee.ticket_type == "VIP")
        if limit:
            q = q.limit(limit)

        result = await db.execute(q)
        targets = result.scalars().all()
        total = len(targets)
        print(f"Found {total} target attendees with empty vertical_tags.")

        if not confirm:
            print("\nDRY-RUN — sample of first 5:")
            for a in targets[:5]:
                print(f"  {a.name} ({a.company}, {a.ticket_type}) — id={a.id}")
            print("\nRe-run with --confirm to classify + re-embed.")
            return

        classified = 0
        empty_results = 0
        failed = 0
        for i, attendee in enumerate(targets, 1):
            try:
                tags = await classify_verticals(attendee)
                if not tags:
                    empty_results += 1
                    print(f"  [{i}/{total}] {attendee.name}: classifier returned EMPTY (sparse profile?)")
                    continue
                attendee.vertical_tags = tags
                attendee.embedding = await embed_attendee(attendee)
                db.add(attendee)
                classified += 1
                if i <= 10 or i % 50 == 0:
                    print(f"  [{i}/{total}] {attendee.name}: {tags}")
                # Commit in batches of 25 so a mid-run failure doesn't lose
                # everything before it. The classify+embed calls are slow
                # (network-bound) so batch commits are fine.
                if i % 25 == 0:
                    await db.commit()
            except Exception as exc:
                failed += 1
                print(f"  [{i}/{total}] FAILED for {attendee.name}: {exc}")
        await db.commit()

        print(
            f"\nDone. classified={classified}, empty_results={empty_results}, failed={failed}, total_scanned={total}"
        )

        if regen_matches and classified > 0:
            from app.services.matching import MatchingEngine
            engine = MatchingEngine(db)
            print(f"\nRegenerating matches for the {classified} updated attendees...")
            for attendee in targets:
                if not attendee.vertical_tags:
                    continue
                try:
                    new_matches = await engine.generate_matches_for_attendee(
                        attendee.id, top_k=10, clear_existing=True, notify=False,
                    )
                    print(f"  {attendee.name}: {len(new_matches)} matches regenerated")
                except Exception as exc:
                    print(f"  {attendee.name}: regen FAILED: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--confirm", action="store_true", help="Commit (default dry-run).")
    parser.add_argument("--vip-only", action="store_true", help="Restrict to VIP ticket-type.")
    parser.add_argument("--attendee-id", type=str, default=None, help="Target a single attendee.")
    parser.add_argument(
        "--regen-matches", action="store_true",
        help="After classifying, also regen matches via MatchingEngine. Heavy — use only with --attendee-id or small sets.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap for safety.")
    args = parser.parse_args()
    asyncio.run(main(
        args.confirm, args.vip_only, args.attendee_id, args.regen_matches, args.limit,
    ))
