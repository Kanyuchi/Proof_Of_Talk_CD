# backend/tests/test_adoption_live_active.py
"""GET /dashboard/adoption — cumulative_active and active_last_7d are now
computed LIVE from users.last_login_at / attendees.last_seen_at, with:
  - person-level dedup (a user linked to an attendee counts once)
  - admin + demo exclusion (mirrors the snapshot's _active_*_filter helpers)
  - active_last_7d = distinct people whose max(last_login_at, last_seen_at) >= now-7d

These two fields must NOT be sourced from usage_daily any more.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.api.routes.dashboard as dash


class _Scalar:
    def __init__(self, v):
        self._v = v

    def scalar(self):
        return self._v


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


# ---------------------------------------------------------------------------
# Helpers to build the db mock matching the new query order:
#   1. count(users)                              -> .scalar()
#   2. count(real users)                         -> .scalar()
#   3. count(users where attendee_id not null)   -> .scalar()
#   4. count(attendees)                          -> .scalar()
#   5. signups_by_day group-by                   -> .all()
#   6. count(login_active)                       -> .scalar()
#   7. count(magic_link_active)                  -> .scalar()
#   8. live person rows for cumulative/7d        -> .all()  (NEW — user rows)
#   9. live attendee rows for cumulative/7d      -> .all()  (NEW — attendee rows)
#  10. usage_by_day from usage_daily             -> .all()
# ---------------------------------------------------------------------------

def _make_db_live(
    *,
    total=10,
    real=8,
    linked=8,
    directory=100,
    signups=None,
    login_active=3,
    magic_link_active=2,
    # live person dedup inputs
    user_rows=None,        # list[(attendee_id_or_None, last_login_at)]
    attendee_rows=None,    # list[(attendee_id, last_seen_at)]
    # trend chart (unchanged)
    usage_by_day_rows=None,
):
    signups = signups or []
    user_rows = user_rows if user_rows is not None else []
    attendee_rows = attendee_rows if attendee_rows is not None else []
    usage_by_day_rows = usage_by_day_rows if usage_by_day_rows is not None else []

    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(total),
        _Scalar(real),
        _Scalar(linked),
        _Scalar(directory),
        _Rows(signups),
        _Scalar(login_active),
        _Scalar(magic_link_active),
        _Rows(user_rows),
        _Rows(attendee_rows),
        _Rows(usage_by_day_rows),
    ]
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cumulative_active_counts_login_only_users():
    """A user with last_login_at set (no attendee link) counts once."""
    user_rows = [(None, datetime(2026, 5, 20))]
    attendee_rows = []
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 1


@pytest.mark.asyncio
async def test_cumulative_active_counts_magic_link_only_account_holders():
    """An attendee row returned by the SQL filter represents a person whose
    account exists (filter requires it as of 2026-05-29) but who has only ever
    used the magic-link path — last_login_at is NULL so they're absent from
    user_rows. They must count once."""
    aid = uuid.uuid4()
    user_rows = []
    attendee_rows = [(aid, datetime(2026, 5, 20))]
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 1


@pytest.mark.asyncio
async def test_cumulative_active_deduplicates_person_with_both():
    """A person with both login and magic-link (linked via attendee_id) counts ONCE."""
    aid = uuid.uuid4()
    user_rows = [(aid, datetime(2026, 5, 22))]      # login
    attendee_rows = [(aid, datetime(2026, 5, 21))]  # magic-link open, same person
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 1, (
        "person with both login + magic-link must be counted once, not twice"
    )


@pytest.mark.asyncio
async def test_cumulative_active_two_distinct_people():
    """Two completely separate people (different attendee_ids) count as 2."""
    aid_a = uuid.uuid4()
    aid_b = uuid.uuid4()
    user_rows = [(aid_a, datetime(2026, 5, 22))]
    attendee_rows = [(aid_b, datetime(2026, 5, 21))]
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 2


@pytest.mark.asyncio
async def test_active_last_7d_includes_recent():
    """A person active within the last 7 days is counted in active_last_7d."""
    aid = uuid.uuid4()
    recent = datetime.utcnow() - timedelta(days=3)
    user_rows = [(aid, recent)]
    attendee_rows = []
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["active_last_7d"] == 1


@pytest.mark.asyncio
async def test_active_last_7d_excludes_older():
    """A person whose most-recent activity is older than 7 days is NOT in active_last_7d."""
    aid = uuid.uuid4()
    old = datetime.utcnow() - timedelta(days=10)
    user_rows = [(aid, old)]
    attendee_rows = []
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 1  # still ever-active
    assert out["usage"]["active_last_7d"] == 0     # outside 7-day window


@pytest.mark.asyncio
async def test_active_last_7d_uses_max_of_login_and_magic():
    """For a linked person, use max(last_login_at, last_seen_at) for the 7d window."""
    aid = uuid.uuid4()
    # login was 10 days ago, magic-link was 2 days ago → should count in 7d
    old_login = datetime.utcnow() - timedelta(days=10)
    recent_magic = datetime.utcnow() - timedelta(days=2)
    user_rows = [(aid, old_login)]
    attendee_rows = [(aid, recent_magic)]
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 1
    assert out["usage"]["active_last_7d"] == 1, (
        "max(login_at, seen_at) within 7d should qualify person for active_last_7d"
    )


@pytest.mark.asyncio
async def test_active_last_7d_deduplicates():
    """A person active in 7d via both login and magic counts once in active_last_7d."""
    aid = uuid.uuid4()
    recent = datetime.utcnow() - timedelta(days=1)
    user_rows = [(aid, recent)]
    attendee_rows = [(aid, recent)]  # same person, same timeframe
    db = _make_db_live(user_rows=user_rows, attendee_rows=attendee_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["active_last_7d"] == 1


@pytest.mark.asyncio
async def test_cumulative_active_zero_when_no_activity():
    """No user/attendee activity → cumulative_active and active_last_7d are 0."""
    db = _make_db_live(user_rows=[], attendee_rows=[])
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage"]["cumulative_active"] == 0
    assert out["usage"]["active_last_7d"] == 0


@pytest.mark.asyncio
async def test_usage_by_day_still_comes_from_snapshot():
    """usage_by_day trend chart is still sourced from usage_daily (unchanged)."""
    usage_rows = [(date(2026, 5, 24), 4, 9)]
    db = _make_db_live(usage_by_day_rows=usage_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage_by_day"] == [
        {"day": "2026-05-24", "active_today": 4, "cumulative_active": 9}
    ]


@pytest.mark.asyncio
async def test_live_active_does_not_affect_usage_by_day():
    """cumulative_active computed live ≠ cumulative in usage_by_day (different sources)."""
    aid = uuid.uuid4()
    user_rows = [(aid, datetime(2026, 5, 23))]
    usage_rows = [(date(2026, 5, 24), 2, 99)]  # snapshot has stale/different number
    db = _make_db_live(user_rows=user_rows, usage_by_day_rows=usage_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    # Live count (1) != snapshot's cumulative_active (99) — they're separate
    assert out["usage"]["cumulative_active"] == 1
    assert out["usage_by_day"][0]["cumulative_active"] == 99


@pytest.mark.asyncio
async def test_tracking_started_at_still_from_snapshot():
    """tracking_started_at is still the first day in usage_daily (unchanged)."""
    usage_rows = [
        (date(2026, 5, 10), 1, 1),
        (date(2026, 5, 11), 2, 3),
    ]
    db = _make_db_live(usage_by_day_rows=usage_rows)
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["tracking_started_at"] == "2026-05-10"
