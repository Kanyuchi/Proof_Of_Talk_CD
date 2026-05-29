"""One-shot cleanup for duplicate Match rows on the same (a, b) pair.

Background: `matches` has no unique constraint on (attendee_a_id, attendee_b_id).
The TOCTOU race in `_persist_ranked` + `_apply_priority_intros` (check-then-insert
without ON CONFLICT) creates duplicate Match rows under concurrent profile saves.
Verified 2026-05-29: 39 dup pairs in prod, 13,213 total matches.

This script picks the strongest row per pair and deletes the rest, so the
follow-up migration can add the unique index without IntegrityError.

Per-pair winner ranking (higher score wins):
- 1000 if met_at set            (actual meeting happened)
- 500  if meeting_time set       (scheduled meeting)
- 200  if tier='priority_intro'  (Elliptic-curated intros — never drop)
- 100  per accepted_*_at set
- 50   per status_*='accepted'
- 25   if decline_reason set
- 10   if hidden_by_user
- 5    if tier='curated'
- 1    if tier='deep'
- Tiebreaker: oldest created_at wins (more stable).

Usage:
    python scripts/dedupe_match_pairs.py            # dry-run
    python scripts/dedupe_match_pairs.py --confirm  # commit deletes
"""
import argparse
import asyncio
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, delete  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Match  # noqa: E402


def _score(m: Match) -> int:
    """Higher = stronger = keep this row."""
    s = 0
    if m.met_at:
        s += 1000
    if m.meeting_time:
        s += 500
    if m.tier == "priority_intro":
        s += 200
    if m.accepted_a_at:
        s += 100
    if m.accepted_b_at:
        s += 100
    if m.status_a == "accepted":
        s += 50
    if m.status_b == "accepted":
        s += 50
    if m.decline_reason:
        s += 25
    if m.hidden_by_user:
        s += 10
    if m.tier == "curated":
        s += 5
    elif m.tier == "deep":
        s += 1
    return s


def _pair_key(m: Match) -> tuple:
    a, b = str(m.attendee_a_id), str(m.attendee_b_id)
    return (a, b) if a < b else (b, a)


async def main(confirm: bool) -> int:
    async with async_session() as db:
        result = await db.execute(select(Match))
        matches = list(result.scalars().all())
        print(f"Loaded {len(matches)} Match rows from prod.")

        by_pair: dict[tuple, list[Match]] = defaultdict(list)
        for m in matches:
            by_pair[_pair_key(m)].append(m)

        dup_pairs = {k: v for k, v in by_pair.items() if len(v) > 1}
        print(f"Pairs with >1 row: {len(dup_pairs)}")
        if not dup_pairs:
            return 0

        to_delete_ids: list = []
        preview_shown = 0
        for pair, rows in dup_pairs.items():
            # Sort by score DESC, then created_at ASC (oldest tiebreaker wins).
            rows.sort(key=lambda r: (-_score(r), r.created_at))
            keep = rows[0]
            drop = rows[1:]
            to_delete_ids.extend(m.id for m in drop)
            if preview_shown < 5:
                print(f"\nPair {pair[0][:8]} / {pair[1][:8]}:")
                for r in rows:
                    flag = "KEEP" if r is keep else "DROP"
                    print(
                        f"  {flag} {str(r.id)[:8]} score={_score(r):4} tier={r.tier or '.':<14} "
                        f"status={r.status} created={r.created_at}"
                    )
                preview_shown += 1

        print(f"\nPlan: delete {len(to_delete_ids)} duplicate Match row(s) across {len(dup_pairs)} pair(s).")

        if not confirm:
            print("\nDry run. Re-run with --confirm to delete.")
            return 0

        # Single atomic delete
        result = await db.execute(delete(Match).where(Match.id.in_(to_delete_ids)))
        await db.commit()
        print(f"\nDeleted {result.rowcount} Match row(s). Re-running audit...")

        # Verify
        result = await db.execute(select(Match))
        all_after = list(result.scalars().all())
        by_pair_after: dict[tuple, list[Match]] = defaultdict(list)
        for m in all_after:
            by_pair_after[_pair_key(m)].append(m)
        remaining_dups = sum(1 for v in by_pair_after.values() if len(v) > 1)
        print(f"  Total matches: {len(all_after)} (was {len(matches)})")
        print(f"  Remaining dup pairs: {remaining_dups}")
        return 0 if remaining_dups == 0 else 1


def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--confirm", action="store_true", help="Commit deletes.")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(_cli().confirm)))
