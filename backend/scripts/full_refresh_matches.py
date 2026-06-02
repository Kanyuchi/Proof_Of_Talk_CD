"""Full match refresh — applies the post-2026-05-29 filter changes.

Iterates every embedded, non-admin attendee and runs
generate_matches_for_attendee(clear_existing=True, notify=False).

clear_existing=True takes the safe path: refreshes stale pending Match rows
IN PLACE (stable match id) and PRESERVES rows where either side has acted
(accepted, declined, hidden, scheduled). Dropped candidates are pruned. See
_collect_locked_counterparts / _prune_unreferenced_pending in matching.py.

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
PER_ATTENDEE_TIMEOUT = 180  # seconds — added after a single OpenAI/DB call hung indefinitely at #1261 in the first run, freezing the loop for 9h with no failure raised.


async def main() -> None:
    # Optional: resume mid-run after a crash/kill. Skip the first N attendees.
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0

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

    print(f"[refresh] {len(targets)} attendees to process (resuming from idx {start_idx})", flush=True)
    start = time.time()
    failed = 0
    total_matches = 0

    for i, (attendee_id, name) in enumerate(targets):
        if i < start_idx:
            continue
        try:
            async with async_session() as session:
                engine = MatchingEngine(session)
                matches = await asyncio.wait_for(
                    engine.generate_matches_for_attendee(
                        attendee_id,
                        top_k=10,
                        clear_existing=True,
                        notify=False,
                    ),
                    timeout=PER_ATTENDEE_TIMEOUT,
                )
                total_matches += len(matches)
        except asyncio.TimeoutError:
            failed += 1
            print(f"[refresh] {i+1}/{len(targets)} TIMEOUT {name!r} (>{PER_ATTENDEE_TIMEOUT}s)", flush=True)
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
