"""Pin the contract that profile-save match-regen preserves user decisions.

David Chapman (Summ, EMEA) reported on 2026-05-26 that the app was:
  - "deleting matches that have been confirmed"  -> accepted/scheduled wiped
  - "suggesting matches I've declined"           -> decline history wiped,
                                                    declined counterpart re-suggested

Root cause: refresh_profile_matches → generate_matches_for_attendee with the
default clear_existing=True ran an unconditional sql_delete(Match) of every
row touching the attendee on every profile save, silently destroying
status_a/status_b/meeting_time/decline_reason. The fix preserves any match
row with user input (from either side) and locks those counterparts out of
new candidate generation.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.matching import MatchingEngine


def _fake_db(survivors_rows=()):
    db = MagicMock()
    result = MagicMock()
    result.all = MagicMock(return_value=list(survivors_rows))
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_purge_helper_returns_locked_counterparts():
    """After the conditional delete, the helper returns every counterpart id
    in the surviving (locked) matches — so they can be excluded from new
    candidate generation to (a) never duplicate a locked pair and (b) never
    resurface a previously-declined counterpart."""
    me = uuid.uuid4()
    other_a = uuid.uuid4()
    other_b = uuid.uuid4()
    # Survivors: I'm the a-side of one match, the b-side of another.
    survivors = [(me, other_a), (other_b, me)]

    db = _fake_db(survivors_rows=survivors)
    engine = MatchingEngine(db)

    locked = await engine._purge_stale_matches_and_collect_locked(me)

    assert locked == {other_a, other_b}
    # one delete + one select were executed
    assert db.execute.await_count >= 2
    # commit fired between delete and survivor select
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_purge_delete_filter_only_targets_untouched_rows():
    """The DELETE must restrict to pending/pending rows with no meeting, no
    decline reason, no hide, no met_at — i.e. fully stale. The compiled SQL
    must reference each of those columns so a future refactor that drops a
    condition (and accidentally re-broadens the delete) is caught here.
    """
    me = uuid.uuid4()
    db = _fake_db(survivors_rows=[])
    engine = MatchingEngine(db)

    await engine._purge_stale_matches_and_collect_locked(me)

    # First execute call = the DELETE statement.
    delete_stmt = db.execute.await_args_list[0].args[0]
    sql = str(delete_stmt.compile(compile_kwargs={"literal_binds": False}))
    for required in ("status_a", "status_b", "meeting_time", "decline_reason",
                     "hidden_by_user", "met_at"):
        assert required in sql, (
            f"DELETE must filter on `{required}` so a regen never wipes a "
            f"match the user has touched. Compiled SQL:\n{sql}"
        )
