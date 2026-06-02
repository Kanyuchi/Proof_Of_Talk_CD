"""Pin the contract that profile-save match-regen preserves user decisions
AND keeps match ids stable across regens.

David Chapman (Summ, EMEA) reported on 2026-05-26 that the app was:
  - "deleting matches that have been confirmed"  -> accepted/scheduled wiped
  - "suggesting matches I've declined"           -> decline history wiped,
                                                    declined counterpart re-suggested

That first fix preserved user-touched rows but still DELETED stale pending rows
up front and re-INSERTED them with a fresh UUID on every regen. On 2026-06-02
(Jesus Lander, live event) that surfaced a second bug: a client holding the old
match id 404'd on accept/decline, so accepts silently failed and rejected
matches reappeared (the decline never persisted). Constant churn came from any
counterpart editing their profile.

Fix (2026-06-02): regen is now non-destructive. `_collect_locked_counterparts`
returns user-touched counterparts (excluded from candidate gen) WITHOUT
deleting; `_persist_ranked` refreshes a stale pending row IN PLACE (stable id);
`_prune_unreferenced_pending` removes only dropped, untouched candidates and
never the rows just re-persisted.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.attendee import Match
from app.services.matching import MatchingEngine


def _fake_db(rows=()):
    db = MagicMock()
    result = MagicMock()
    result.all = MagicMock(return_value=list(rows))
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_collect_locked_counterparts_is_non_destructive():
    """Returns every counterpart id carrying user input — and runs NO delete.
    The pre-2026-06-02 purge deleted stale rows here; deleting them is exactly
    what forced fresh match ids on regen, so the helper must never delete."""
    me = uuid.uuid4()
    other_a = uuid.uuid4()
    other_b = uuid.uuid4()
    locked_rows = [(me, other_a), (other_b, me)]

    db = _fake_db(rows=locked_rows)
    engine = MatchingEngine(db)

    locked = await engine._collect_locked_counterparts(me)

    assert locked == {other_a, other_b}
    # Exactly one statement (the SELECT) — and it must NOT be a DELETE.
    assert db.execute.await_count == 1
    stmt = db.execute.await_args_list[0].args[0]
    assert stmt.__visit_name__ == "select", "locked-counterpart collection must not delete"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_prune_deletes_only_untouched_rows_and_respects_keep_ids():
    """The prune DELETE must restrict to pending/pending rows with no meeting,
    no decline reason, no hide, no met_at — and must exclude the ids re-persisted
    this run (keep_ids). A future refactor dropping any guard is caught here."""
    me = uuid.uuid4()
    keep = {uuid.uuid4(), uuid.uuid4()}
    db = _fake_db()
    engine = MatchingEngine(db)

    await engine._prune_unreferenced_pending(me, keep_ids=keep)

    delete_stmt = db.execute.await_args_list[0].args[0]
    assert delete_stmt.__visit_name__ == "delete"
    sql = str(delete_stmt.compile(compile_kwargs={"literal_binds": False}))
    for required in ("status_a", "status_b", "meeting_time", "decline_reason",
                     "hidden_by_user", "met_at"):
        assert required in sql, (
            f"prune DELETE must filter on `{required}` so a regen never removes "
            f"a match the user has touched. Compiled SQL:\n{sql}"
        )
    # keep_ids -> a NOT IN (...) guard so just-persisted survivors are spared.
    assert "NOT IN" in sql.upper(), "prune must spare re-persisted rows via keep_ids"
    db.commit.assert_awaited()


def _stale_match(a, b):
    return Match(
        id=uuid.uuid4(), attendee_a_id=a, attendee_b_id=b,
        similarity_score=0.5, complementary_score=0.5, overall_score=0.5,
        match_type="complementary", explanation="old", shared_context={},
        status="pending", status_a="pending", status_b="pending",
        meeting_time=None, decline_reason=None, hidden_by_user=False, met_at=None,
    )


def _is_stale_helper_matrix():
    me, other = uuid.uuid4(), uuid.uuid4()
    stale = _stale_match(me, other)
    accepted = _stale_match(me, other); accepted.status_a = "accepted"
    declined = _stale_match(me, other); declined.decline_reason = "not relevant"
    hidden = _stale_match(me, other); hidden.hidden_by_user = True
    return stale, accepted, declined, hidden


def test_is_stale_pending_matrix():
    stale, accepted, declined, hidden = _is_stale_helper_matrix()
    assert MatchingEngine._is_stale_pending(stale) is True
    assert MatchingEngine._is_stale_pending(accepted) is False
    assert MatchingEngine._is_stale_pending(declined) is False
    assert MatchingEngine._is_stale_pending(hidden) is False


@pytest.mark.asyncio
async def test_persist_reuses_stale_row_in_place_keeping_id():
    """When a stale pending row already exists for the pair, _persist_ranked
    must REFRESH it in place (same id) and add NO new row — this is what keeps
    accept/decline working across regens."""
    me_id, other_id = uuid.uuid4(), uuid.uuid4()
    attendee = SimpleNamespace(id=me_id)
    candidate = SimpleNamespace(id=other_id)
    existing = _stale_match(me_id, other_id)
    original_id = existing.id

    db = MagicMock()
    sel_result = MagicMock()
    sel_result.scalars.return_value.first.return_value = existing
    db.execute = AsyncMock(return_value=sel_result)
    db.flush = AsyncMock()
    db.add = MagicMock()
    engine = MatchingEngine(db)

    ranked = [{
        "candidate_index": 1, "overall_score": 0.91, "complementary_score": 0.88,
        "match_type": "complementary", "explanation": "fresh reasoning",
        "shared_context": {"x": 1}, "explanation_confidence": 0.9,
    }]
    persisted = await engine._persist_ranked(
        attendee, ranked, [(candidate, 0.91)],
        tier="curated", floor=0.0, non_obvious_floor=0.0,
    )

    assert persisted == [existing]
    assert existing.id == original_id, "match id must stay stable"
    assert existing.overall_score == 0.91 and existing.explanation == "fresh reasoning"
    db.add.assert_not_called(), "must reuse, not insert a duplicate row"


@pytest.mark.asyncio
async def test_persist_never_overwrites_user_touched_row():
    """A row the user accepted/declined must be left exactly as-is — never
    refreshed and never re-inserted."""
    me_id, other_id = uuid.uuid4(), uuid.uuid4()
    attendee = SimpleNamespace(id=me_id)
    candidate = SimpleNamespace(id=other_id)
    accepted = _stale_match(me_id, other_id)
    accepted.status_a = "accepted"
    accepted.explanation = "user already accepted this"

    db = MagicMock()
    sel_result = MagicMock()
    sel_result.scalars.return_value.first.return_value = accepted
    db.execute = AsyncMock(return_value=sel_result)
    db.flush = AsyncMock()
    db.add = MagicMock()
    engine = MatchingEngine(db)

    ranked = [{
        "candidate_index": 1, "overall_score": 0.99, "complementary_score": 0.99,
        "match_type": "complementary", "explanation": "regen wants to overwrite",
        "shared_context": {}, "explanation_confidence": 0.9,
    }]
    persisted = await engine._persist_ranked(
        attendee, ranked, [(candidate, 0.99)],
        tier="curated", floor=0.0, non_obvious_floor=0.0,
    )

    assert persisted == []
    assert accepted.status_a == "accepted"
    assert accepted.explanation == "user already accepted this", "user-touched row must be untouched"
    db.add.assert_not_called()
