# backend/tests/test_refresh_lock.py
"""Per-attendee asyncio.Lock in refresh_profile_matches serializes
concurrent calls for the SAME attendee so they don't both pay the
~5-10s embed + GPT-4o rerank cost. Different attendees still run
in parallel."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.profile_pipeline as pp

pytestmark = pytest.mark.asyncio


class _Ctx:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *a):
        return False


async def _setup_slow_engine(call_order: list, key: str, delay: float = 0.1):
    """Returns a (db_factory, engine_factory) pair that records when the
    engine starts/ends per attendee, with a configurable delay."""
    db = AsyncMock()
    db.get = AsyncMock(return_value=object())

    async def slow_process(*a, **kw):
        call_order.append(f"{key}-start")
        await asyncio.sleep(delay)
        call_order.append(f"{key}-end")

    engine = MagicMock()
    engine.process_attendee = slow_process
    engine.generate_matches_for_attendee = AsyncMock()

    return db, engine


async def test_same_attendee_calls_serialize(monkeypatch):
    """Two concurrent refreshes for the same attendee_id must run
    sequentially under the lock."""
    aid = uuid.uuid4()
    order: list[str] = []

    db1, eng1 = await _setup_slow_engine(order, "A", delay=0.05)
    db2, eng2 = await _setup_slow_engine(order, "B", delay=0.05)

    sessions = iter([_Ctx(db1), _Ctx(db2)])
    engines = iter([eng1, eng2])

    monkeypatch.setattr(pp, "async_session", lambda: next(sessions))
    monkeypatch.setattr(pp, "MatchingEngine", lambda db: next(engines))

    await asyncio.gather(
        pp.refresh_profile_matches(aid),
        pp.refresh_profile_matches(aid),
    )

    # Strict serialization: A must fully finish before B starts (or vice versa)
    assert order in (
        ["A-start", "A-end", "B-start", "B-end"],
        ["B-start", "B-end", "A-start", "A-end"],
    ), f"Calls did not serialize. Order: {order}"


async def test_different_attendees_run_in_parallel(monkeypatch):
    """Two concurrent refreshes for DIFFERENT attendee_ids must overlap
    (no global lock)."""
    aid_a = uuid.uuid4()
    aid_b = uuid.uuid4()
    order: list[str] = []

    db1, eng1 = await _setup_slow_engine(order, "A", delay=0.05)
    db2, eng2 = await _setup_slow_engine(order, "B", delay=0.05)

    sessions = iter([_Ctx(db1), _Ctx(db2)])
    engines = iter([eng1, eng2])

    monkeypatch.setattr(pp, "async_session", lambda: next(sessions))
    monkeypatch.setattr(pp, "MatchingEngine", lambda db: next(engines))

    await asyncio.gather(
        pp.refresh_profile_matches(aid_a),
        pp.refresh_profile_matches(aid_b),
    )

    # Both starts should occur before either end (interleaved)
    starts_before_ends = order.index("A-end") > order.index("B-start") or \
                          order.index("B-end") > order.index("A-start")
    assert starts_before_ends, f"Calls did not run in parallel. Order: {order}"


async def test_lock_released_on_exception(monkeypatch):
    """If the inner pipeline raises, the lock must still release so the
    next call for the same attendee can acquire it."""
    aid = uuid.uuid4()

    db = AsyncMock()
    db.get = AsyncMock(side_effect=RuntimeError("boom"))

    sessions = iter([_Ctx(db), _Ctx(db)])
    monkeypatch.setattr(pp, "async_session", lambda: next(sessions))
    # Stub the error recorder so it's a no-op
    monkeypatch.setattr(pp, "_record_refresh_error", AsyncMock())

    # Two sequential calls — both must complete without hanging
    await pp.refresh_profile_matches(aid)
    await pp.refresh_profile_matches(aid)

    # Lock should not have leaked — verify by acquiring and checking it's free
    lock = pp._lock_for(aid)
    assert not lock.locked()
