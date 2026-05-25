# backend/tests/test_adoption_endpoint.py
"""GET /dashboard/adoption — admin-gating, shape, real/demo exclusion, pct math."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.api.routes.dashboard as dash


class _Scalar:
    def __init__(self, v): self._v = v
    def scalar(self): return self._v


class _Rows:
    def __init__(self, rows): self._rows = rows
    def all(self): return self._rows


def _make_db():
    """Sequence the queries the handler issues, in order:
      1. count(users)                      -> .scalar()  (accounts.total)
      2. count(real users)                 -> .scalar()  (accounts.real)
      3. count(users where attendee_id not null) -> .scalar() (linked_to_attendee)
      4. count(attendees)                  -> .scalar()  (directory_size)
      5. signups_by_day group-by           -> .all()  [(date, n)]
      6. count(distinct login_active)      -> .scalar()
      7. count(distinct magic_active)      -> .scalar()
      8. live user rows (attendee_id, last_login_at) -> .all()  [LIVE cumulative/7d]
      9. live attendee rows (id, last_seen_at)       -> .all()  [LIVE cumulative/7d]
     10. usage_by_day select from usage_daily        -> .all() [(day, active_today, cumulative_active)]
    """
    import uuid as _uuid
    from datetime import datetime as _dt, timedelta as _td
    _aid = _uuid.uuid4()
    _recent = _dt.utcnow() - _td(days=1)
    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(162),                                   # total
        _Scalar(154),                                   # real
        _Scalar(161),                                   # linked_to_attendee
        _Scalar(912),                                   # directory_size
        _Rows([(date(2026, 5, 21), 46), (date(2026, 5, 22), 50)]),  # signups
        _Scalar(3),                                     # login_active
        _Scalar(7),                                     # magic_link_active
        _Rows([(_aid, _recent)]),                       # live user rows
        _Rows([]),                                      # live attendee rows
        _Rows([                                         # usage_by_day
            (date(2026, 5, 24), 4, 9),
        ]),
    ]
    return db


@pytest.mark.asyncio
async def test_adoption_shape_and_pct_math():
    db = _make_db()
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))

    assert out["accounts"]["total"] == 162
    assert out["accounts"]["real"] == 154
    assert out["accounts"]["linked_to_attendee"] == 161
    assert out["accounts"]["directory_size"] == 912
    assert out["accounts"]["pct_of_directory"] == round(154 / 912 * 100, 1)

    assert out["signups_by_day"] == [
        {"day": "2026-05-21", "n": 46},
        {"day": "2026-05-22", "n": 50},
    ]

    assert out["usage"]["login_active"] == 3
    assert out["usage"]["magic_link_active"] == 7
    # cumulative_active / active_last_7d are now computed LIVE from user/attendee
    # rows, not from usage_daily. _make_db feeds 1 live user row → 1 person.
    assert out["usage"]["cumulative_active"] == 1
    assert out["usage"]["active_last_7d"] == 1  # the seeded user was recent

    # usage_by_day trend chart still comes from usage_daily (unchanged)
    assert out["usage_by_day"] == [
        {"day": "2026-05-24", "active_today": 4, "cumulative_active": 9},
    ]
    assert out["tracking_started_at"] == "2026-05-24"  # min(day) in usage_daily


@pytest.mark.asyncio
async def test_adoption_empty_usage_falls_back_to_today():
    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(0), _Scalar(0), _Scalar(0), _Scalar(0),  # accounts + directory
        _Rows([]),                                         # signups
        _Scalar(0), _Scalar(0),                            # login_active / magic_link_active
        _Rows([]),                                         # live user rows (empty)
        _Rows([]),                                         # live attendee rows (empty)
        _Rows([]),                                         # usage_by_day EMPTY
    ]
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage_by_day"] == []
    assert out["accounts"]["pct_of_directory"] == 0.0   # no div-by-zero
    assert out["tracking_started_at"] == datetime.utcnow().date().isoformat()
    assert out["usage"]["cumulative_active"] == 0
    assert out["usage"]["active_last_7d"] == 0


def test_adoption_requires_admin_dependency():
    """The route is wired with require_admin (not require_auth)."""
    import inspect
    sig = inspect.signature(dash.get_adoption)
    dep = sig.parameters["_admin"].default
    # FastAPI Depends wraps the callable; assert it points at require_admin.
    assert getattr(dep, "dependency", None) is dash.require_admin
