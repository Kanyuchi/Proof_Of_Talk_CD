# backend/tests/test_matching_pair_uniqueness.py
"""Race-guard for the (attendee_a_id, attendee_b_id) unique index added
by migration c4f1a2e8b3d7. When a concurrent writer wins the insert race,
the loser's flush throws IntegrityError; the savepoint should roll back
just that one row and the loop should continue to the next match instead
of aborting the entire transaction.

Tests both Match-insert call sites in matching.py:
- _persist_ranked (curated + deep tiers)
- _apply_priority_intros (force-add path)
"""
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.attendee import Match, RequestedIntro
from app.services.matching import MatchingEngine

pytestmark = pytest.mark.asyncio


def _att(name="A", aid=None):
    return SimpleNamespace(
        id=aid or uuid.uuid4(),
        name=name,
        title="CEO",
        company="Co",
        goals="",
        ai_summary=None,
        interests=[],
        vertical_tags=[],
        intent_tags=[],
        deal_readiness_score=0.5,
        embedding=[0.1] * 1536,
        enriched_profile={},
        inferred_customer_profile={},
        ticket_type="GA",
        not_looking_for=[],
        preferred_geographies=[],
        deal_stage=None,
        seeking=[],
        privacy_mode="full",
        email="a@b.co",
        email_opt_out=False,
        magic_access_token=None,
        ai_summary_pinned=False,
    )


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _NestedCM:
    """Mock context manager for `async with db.begin_nested()`. Either
    succeeds normally OR raises IntegrityError on flush (via the parent
    db.flush being patched)."""

    def __init__(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # If an exception was raised inside the block, let it propagate.
        return False


async def _persist_ranked_setup(integrity_on_calls: list[int]):
    """integrity_on_calls = list of 0-indexed flush call counts that should
    raise IntegrityError. e.g. [0] = first flush raises; [1] = second; [] = none."""
    requester = _att("Alice")
    target1 = _att("Bob")
    target2 = _att("Carol")

    db = AsyncMock()
    db.begin_nested = MagicMock(side_effect=lambda: _NestedCM())

    flush_calls = {"n": 0}

    async def fake_flush():
        n = flush_calls["n"]
        flush_calls["n"] += 1
        if n in integrity_on_calls:
            # SQLAlchemy IntegrityError takes (statement, params, orig)
            raise IntegrityError("INSERT INTO matches", {}, Exception("dup"))

    db.flush = fake_flush

    # First SELECT in _persist_ranked: existing-match check (returns None twice)
    db.execute = AsyncMock(side_effect=[
        _Rows([]),  # existing check for target1
        _Rows([]),  # existing check for target2
    ])

    engine = MatchingEngine(db)
    ranked = [
        {"candidate_index": 1, "overall_score": 0.9, "complementary_score": 0.9,
         "match_type": "complementary", "explanation": "x", "shared_context": {}},
        {"candidate_index": 2, "overall_score": 0.85, "complementary_score": 0.85,
         "match_type": "complementary", "explanation": "y", "shared_context": {}},
    ]
    candidates = [(target1, 0.9), (target2, 0.85)]
    return engine, requester, ranked, candidates


async def test_persist_ranked_skips_when_race_wins_other_writer():
    """First flush raises IntegrityError (other writer beat us to that pair).
    The second match should still persist successfully."""
    engine, requester, ranked, candidates = await _persist_ranked_setup(
        integrity_on_calls=[0]
    )
    persisted = await engine._persist_ranked(
        requester, ranked, candidates,
        tier="curated", floor=0.0, non_obvious_floor=0.0,
    )
    # Only the second match landed; the first was a no-op skip on IntegrityError
    assert len(persisted) == 1
    assert persisted[0].attendee_b_id == candidates[1][0].id


async def test_persist_ranked_all_succeed_when_no_race():
    """No IntegrityError: both matches land normally."""
    engine, requester, ranked, candidates = await _persist_ranked_setup(
        integrity_on_calls=[]
    )
    persisted = await engine._persist_ranked(
        requester, ranked, candidates,
        tier="curated", floor=0.0, non_obvious_floor=0.0,
    )
    assert len(persisted) == 2


async def test_persist_ranked_all_lose_when_total_race():
    """Both flushes IntegrityError: empty result, no crash."""
    engine, requester, ranked, candidates = await _persist_ranked_setup(
        integrity_on_calls=[0, 1]
    )
    persisted = await engine._persist_ranked(
        requester, ranked, candidates,
        tier="curated", floor=0.0, non_obvious_floor=0.0,
    )
    assert persisted == []


async def test_apply_priority_intros_force_add_handles_race():
    """_apply_priority_intros force-add path also savepoint-wraps."""
    requester = _att("Aylin")
    target = _att("Bob")

    intro = SimpleNamespace(
        id=uuid.uuid4(),
        requester_attendee_id=requester.id,
        target_attendee_id=target.id,
        target_name_raw="Bob at Co",
        target_company_raw="Co",
        source="test",
        added_at=datetime.utcnow(),
        resolved_at=None,
    )

    db = AsyncMock()
    db.begin_nested = MagicMock(side_effect=lambda: _NestedCM())

    flush_calls = {"n": 0}
    async def fake_flush():
        flush_calls["n"] += 1
        raise IntegrityError("INSERT INTO matches", {}, Exception("dup"))
    db.flush = fake_flush

    db.execute = AsyncMock(side_effect=[
        _Rows([intro]),     # SELECT RequestedIntro
        _Rows([target]),    # SELECT Attendee for missing target hydration
        _Rows([]),          # SELECT existing Match for the pair -> none, so insert
    ])
    db.commit = AsyncMock()

    engine = MatchingEngine(db)
    result = await engine._apply_priority_intros(requester, [])

    # The force-add IntegrityError'd, so the result list stays empty
    # (no Match was added). The commit still runs so any tier upgrades stick.
    assert result == []
    assert db.commit.await_count == 1
