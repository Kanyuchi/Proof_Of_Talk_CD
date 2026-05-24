# backend/tests/test_usage_snapshot.py
"""usage_snapshot.compute_and_upsert_usage_daily — correctness + idempotency."""

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.services.usage_snapshot as us


class _Scalar:
    """Wrap a scalar value for `(await db.execute(...)).scalar()`."""
    def __init__(self, v): self._v = v
    def scalar(self): return self._v


class _Rows:
    """Wrap rows for `(await db.execute(...)).all()` returning (a, b) tuples."""
    def __init__(self, rows): self._rows = rows
    def all(self): return self._rows


def _make_db(*, total, real, users_active, attendees_active, upsert_sink):
    """users_active: list[(attendee_id_or_None, last_login_at)].
    attendees_active: list[(attendee_id, last_seen_at)].
    The service issues, in order:
      1. count(users)               -> .scalar()
      2. count(real users)          -> .scalar()
      3. select user (attendee_id, last_login_at) where last_login_at not null -> .all()
      4. select attendee (id, last_seen_at) where last_seen_at not null        -> .all()
      5. upsert INSERT ... ON CONFLICT (text())                                -> append to sink
    """
    db = AsyncMock()
    seq = [
        _Scalar(total),
        _Scalar(real),
        _Rows(users_active),
        _Rows(attendees_active),
        None,  # the upsert execute() return is unused
    ]
    async def _execute(stmt, params=None):
        out = seq.pop(0)
        if out is None:  # the upsert
            upsert_sink.append(params)
        return out
    db.execute.side_effect = _execute
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_snapshot_counts_distinct_people_no_double_count():
    aid = uuid.uuid4()
    now = datetime.utcnow()
    sink = []
    # One person logged in AND opened magic link (linked via attendee_id=aid):
    # should count ONCE, not twice.
    db = _make_db(
        total=10, real=8,
        users_active=[(aid, now - timedelta(hours=1))],
        attendees_active=[(aid, now - timedelta(hours=2))],
        upsert_sink=sink,
    )
    stats = await us.compute_and_upsert_usage_daily(db)
    assert stats["total_accounts"] == 10
    assert stats["real_accounts"] == 8
    assert stats["active_today"] == 1        # de-duped
    assert stats["cumulative_active"] == 1
    db.commit.assert_awaited()
    # the upsert was issued with the computed values
    assert sink and sink[0]["total_accounts"] == 10
    assert sink[0]["active_today"] == 1


@pytest.mark.asyncio
async def test_snapshot_magic_only_attendee_counts():
    aid = uuid.uuid4()
    now = datetime.utcnow()
    sink = []
    # A magic-link-only attendee (no user row) active in 24h.
    db = _make_db(
        total=5, real=5,
        users_active=[],
        attendees_active=[(aid, now - timedelta(hours=3))],
        upsert_sink=sink,
    )
    stats = await us.compute_and_upsert_usage_daily(db)
    assert stats["active_today"] == 1
    assert stats["cumulative_active"] == 1


@pytest.mark.asyncio
async def test_snapshot_excludes_stale_from_active_today():
    now = datetime.utcnow()
    sink = []
    db = _make_db(
        total=5, real=5,
        users_active=[(None, now - timedelta(days=3))],   # ever-active but stale
        attendees_active=[],
        upsert_sink=sink,
    )
    stats = await us.compute_and_upsert_usage_daily(db)
    assert stats["active_today"] == 0        # outside 24h
    assert stats["cumulative_active"] == 1   # still ever-active


@pytest.mark.asyncio
async def test_snapshot_upsert_is_idempotent_text():
    """The upsert must be ON CONFLICT (day) DO UPDATE so a same-day re-run
    overwrites rather than erroring."""
    now = datetime.utcnow()
    sink = []
    db = _make_db(
        total=1, real=1, users_active=[(None, now)], attendees_active=[],
        upsert_sink=sink,
    )
    captured = {}
    orig = db.execute.side_effect
    async def _spy(stmt, params=None):
        captured["last_sql"] = str(stmt)
        return await orig(stmt, params)
    db.execute.side_effect = _spy
    await us.compute_and_upsert_usage_daily(db)
    assert "ON CONFLICT" in captured["last_sql"].upper()
    assert "DO UPDATE" in captured["last_sql"].upper()
