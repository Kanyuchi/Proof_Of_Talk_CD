"""Magic-link match list must report whether the viewer already has a User row.

Phase 1 of the magic-link conversion funnel: MagicMatches.tsx needs to default-
expand the "Set your password" panel for unclaimed visitors (those with no
`users` row). It can't know that without a backend signal, so the magic-link
GET response now includes `has_account: bool`.

Same FakeDB pattern as test_magic_matches_viewer.py but tracks call order so
the User lookup can be controlled independently of the Attendee + Match calls.
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

_client = TestClient(app, raise_server_exceptions=False)

_VIEWER_ID = uuid4()


def _make_viewer():
    return SimpleNamespace(
        id=_VIEWER_ID,
        name="Test Viewer",
        email="viewer@example.invalid",
        company="Acme Web3",
        title="Founder",
        ticket_type="DELEGATE",
        interests=["defi"],
        goals="raising a seed round",
        target_companies="a16z crypto",
        seeking=[],
        not_looking_for=[],
        preferred_geographies=[],
        deal_stage=None,
        photo_url=None,
        linkedin_url=None,
        twitter_handle=None,
        company_website=None,
        ai_summary=None,
        intent_tags=[],
        vertical_tags=[],
        deal_readiness_score=None,
        enriched_profile={},
        privacy_mode="full",
        magic_access_token="tok-abcdef-1234567890",
        created_at=datetime(2026, 1, 1),
    )


def _override_db(viewer, *, user_exists: bool):
    """Mocked DB that hands back the right shape per call:
      call 1: Attendee lookup → viewer
      call 2: Match lookup    → no matches (skips _build_match_response)
      call 3: User lookup     → either a fake row or None
    """
    fake_user_id = uuid4() if user_exists else None
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
            self._single = single
            self._many = many

        def scalars(self):
            return _Scalars(self._single, self._many)

    class _FakeDB:
        async def execute(self, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Result(viewer, [viewer])
            if calls["n"] == 2:
                return _Result(None, [])
            return _Result(fake_user_id, [fake_user_id] if user_exists else [])

        async def commit(self):
            # last_seen_at heartbeat; endpoint swallows exceptions but commit
            # exists for cleanliness so we don't rely on the broad except.
            return None

    async def _dep():
        yield _FakeDB()

    return _dep


def test_magic_matches_has_account_false_when_no_user_row():
    """An unclaimed attendee (placeholder-email, ticket-only) has no users row.
    The frontend uses this to default-expand the claim panel."""
    viewer = _make_viewer()
    app.dependency_overrides[get_db] = _override_db(viewer, user_exists=False)
    try:
        r = _client.get("/api/v1/matches/m/tok-abcdef-1234567890")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("has_account") is False, (
        "magic-link response must report has_account=False for unclaimed visitors"
    )


def test_magic_matches_has_account_true_when_user_row_exists():
    """A claimed attendee (already set a password) has a users row.
    The frontend uses this to keep the claim panel collapsed by default."""
    viewer = _make_viewer()
    app.dependency_overrides[get_db] = _override_db(viewer, user_exists=True)
    try:
        r = _client.get("/api/v1/matches/m/tok-abcdef-1234567890")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("has_account") is True, (
        "magic-link response must report has_account=True for claimed visitors"
    )
