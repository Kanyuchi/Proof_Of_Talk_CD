"""Full match refresh — applies the post-2026-05-29 filter changes.

Iterates every embedded, non-admin attendee and runs
generate_matches_for_attendee(clear_existing=True, notify=False).

clear_existing=True takes the safe path: purges stale pending Match rows
but PRESERVES rows where either side has acted (accepted, declined, hidden,
scheduled). See _purge_stale_matches_and_collect_locked in matching.py.

notify=False prevents emailing every attendee an intro to their (now
recomputed) top match — a full refresh must never fan out 360+ emails.

Each attendee is processed in its own session (resilience pattern from
refresh_matches_for_new_attendees — pooler disconnects don't poison the
loop).

Run from backend/ as: python scripts/full_refresh_matches.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Attendee  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.matching import MatchingEngine  # noqa: E402


PROGRESS_EVERY = 10


async def main() -> None:
    async with async_session() as db:
        admin_subq = select(User.attendee_id).where(
            User.is_admin.is_(True),
            User.attendee_id.isnot(None),
        )
        result = await db.execute(
            select(Attendee.id, Attendee.name)
            .where(Attendee.embedding.isnot(None))
            .where(~Attendee.id.in_(admin_subq))
            .order_by(Attendee.created_at)
        )
        targets = list(result.all())

    print(f"[refresh] {len(targets)} attendees to process", flush=True)
    start = time.time()
    failed = 0
    total_matches = 0

    for i, (attendee_id, name) in enumerate(targets):
        try:
            async with async_session() as session:
                engine = MatchingEngine(session)
                matches = await engine.generate_matches_for_attendee(
                    attendee_id,
                    top_k=10,
                    clear_existing=True,
                    notify=False,
                )
                total_matches += len(matches)
        except (DBAPIError, OperationalError, InterfaceError) as exc:
            failed += 1
            print(f"[refresh] {i+1}/{len(targets)} DB drop on {name!r}: {exc}", flush=True)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[refresh] {i+1}/{len(targets)} FAIL {name!r}: {exc}", flush=True)
        else:
            if (i + 1) % PROGRESS_EVERY == 0 or (i + 1) == len(targets):
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0.0
                eta = (len(targets) - (i + 1)) / rate if rate > 0 else 0.0
                print(
                    f"[refresh] {i+1}/{len(targets)} "
                    f"matches={total_matches} failed={failed} "
                    f"elapsed={elapsed:.0f}s rate={rate:.2f}/s eta={eta:.0f}s",
                    flush=True,
                )
        await asyncio.sleep(0)

    elapsed = time.time() - start
    print(
        f"[refresh] DONE in {elapsed:.0f}s — "
        f"processed={len(targets)} matches={total_matches} failed={failed}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
