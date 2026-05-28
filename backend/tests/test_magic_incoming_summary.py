"""Magic-link incoming-summary endpoint backs the Phase 2 reciprocity banner.

The MagicMatches page needs aggregate counts across the FULL match set (not
the capped/visible window), so the banner can read "{N} people accepted your
interest" even when those matches sit below the tier cap.

  - count_pending_for_you: counterpart accepted, the token-holder has not.
  - count_accepted_back:   token-holder accepted AND counterpart also accepted
                           (mutual matches that landed).

Same FakeDB pattern as test_magic_matches_has_account.py.
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

_client = TestClient(app, raise_server_exceptions=False)

_VIEWER_ID = uuid4()
_OTHER_A = uuid4()
_OTHER_B = uuid4()
_OTHER_C = uuid4()
_OTHER_D = uuid4()
_OTHER_E = uuid4()


def _viewer():
    return SimpleNamespace(
        id=_VIEWER_ID,
        magic_access_token="tok-incoming-summary-xyz123",
    )


def _match(a_id, b_id, status_a, status_b):
    return SimpleNamespace(
        attendee_a_id=a_id,
        attendee_b_id=b_id,
        status_a=status_a,
        status_b=status_b,
    )


def _override_db(matches):
    """1st execute → Attendee lookup; 2nd execute → match list."""
    viewer = _viewer()
    calls = {"n": 0}

    class _Scalars:
        def __init__(self, single, many):
            self._single = single
            self._many = many

        def first(self):
            return self._single

        def all(self):
            return self._many

    class _Result:
        def __init__(self, single, many):
            self.s = single
            self.m = many

        def scalars(self):
            return _Scalars(self.s, self.m)

    class _FakeDB:
        async def execute(self, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Result(viewer, [viewer])
            return _Result(None, matches)

    async def _dep():
        yield _FakeDB()

    return _dep


def test_incoming_summary_counts_pending_and_accepted_back():
    matches = [
        # Counterpart accepted, viewer pending → +1 pending_for_you
        _match(_VIEWER_ID, _OTHER_A, "pending", "accepted"),
        # Same on the other side of the dyad (viewer is B)
        _match(_OTHER_B, _VIEWER_ID, "accepted", "pending"),
        # Mutual accepted both sides → +1 accepted_back
        _match(_VIEWER_ID, _OTHER_C, "accepted", "accepted"),
        # Both pending — no count
        _match(_VIEWER_ID, _OTHER_D, "pending", "pending"),
        # Viewer declined, counterpart accepted — not pending_for_you (viewer
        # explicitly responded) and not accepted_back (viewer didn't accept)
        _match(_VIEWER_ID, _OTHER_E, "declined", "accepted"),
    ]
    app.dependency_overrides[get_db] = _override_db(matches)
    try:
        r = _client.get("/api/v1/matches/m/tok-incoming-summary-xyz123/incoming-summary")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {
        "count_pending_for_you": 2,
        "count_accepted_back": 1,
    }


def test_incoming_summary_returns_zeros_when_no_matches():
    app.dependency_overrides[get_db] = _override_db([])
    try:
        r = _client.get("/api/v1/matches/m/tok-incoming-summary-xyz123/incoming-summary")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    assert r.json() == {"count_pending_for_you": 0, "count_accepted_back": 0}


def test_incoming_summary_404_on_unknown_token():
    """Bad token → 404, mirrors the rest of /m/{token} routes."""
    calls = {"n": 0}

    class _Scalars:
        def first(self):
            return None

        def all(self):
            return []

    class _Result:
        def scalars(self):
            return _Scalars()

    class _FakeDB:
        async def execute(self, *a, **k):
            calls["n"] += 1
            return _Result()

    async def _dep():
        yield _FakeDB()

    app.dependency_overrides[get_db] = _dep
    try:
        r = _client.get("/api/v1/matches/m/tok-bad-but-long-enough-1234567890/incoming-summary")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 404, r.text
