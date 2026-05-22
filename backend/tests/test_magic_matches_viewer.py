"""Magic-link match list must carry the viewer's own profile.

Regression test for the no-login enrichment-card bug: MagicMatches.tsx loaded
the viewer via the auth-gated GET /attendees/{id}, which 401s for no-login
users, so the enrichment card (LinkedIn / goals / target_companies / photo
upload) never rendered. The fix surfaces the viewer's profile on the
already-public GET /matches/m/{token} response so the frontend never needs the
gated route.

Endpoint test uses TestClient + dependency_overrides with a mocked DB (this
repo has no test database). Pattern mirrors tests/test_avatars.py.
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

_client = TestClient(app, raise_server_exceptions=False)

_VIEWER_ID = uuid4()


def _make_viewer(**overrides):
    """A complete Attendee-shaped object so AttendeeResponse.model_validate and
    the completeness helpers (profile_data_quality / compute_completeness_pct)
    both read real values."""
    base = dict(
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
    base.update(overrides)
    return SimpleNamespace(**base)


def _override_db_returning(attendee):
    """First execute() (the Attendee lookup) hits .scalars().first(); the second
    (the Match lookup) hits .scalars().all() — returning no matches keeps the
    handler off _build_match_response so we only exercise the viewer payload."""
    class _Scalars:
        def first(self):
            return attendee

        def all(self):
            return []

    class _Result:
        def scalars(self):
            return _Scalars()

    class _FakeDB:
        async def execute(self, *a, **k):
            return _Result()

    async def _dep():
        yield _FakeDB()

    return _dep


def test_magic_matches_includes_viewer_profile():
    viewer = _make_viewer()
    app.dependency_overrides[get_db] = _override_db_returning(viewer)
    try:
        r = _client.get("/api/v1/matches/m/tok-abcdef-1234567890")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["attendee_id"] == str(_VIEWER_ID)
    viewer_payload = body.get("viewer")
    assert viewer_payload is not None, "magic-link response must carry the viewer's own profile"
    # Every field the MagicMatches enrichment card + header + AttendeeAvatar read.
    for field in (
        "name", "title", "company", "photo_url",
        "linkedin_url", "goals", "target_companies", "twitter_handle",
    ):
        assert field in viewer_payload, f"viewer payload missing {field}"
    assert viewer_payload["name"] == "Test Viewer"
    assert viewer_payload["goals"] == "raising a seed round"
    assert viewer_payload["linkedin_url"] is None  # an empty field the card prompts for


def test_magic_matches_viewer_reflects_filled_fields():
    """When a field is filled, it comes back populated (so the card stops
    prompting for it). Guards against returning a stale/empty viewer."""
    viewer = _make_viewer(
        linkedin_url="https://www.linkedin.com/in/testviewer",
        photo_url="https://cdn.example/avatars/x.jpg",
        twitter_handle="testviewer",
    )
    app.dependency_overrides[get_db] = _override_db_returning(viewer)
    try:
        r = _client.get("/api/v1/matches/m/tok-abcdef-1234567890")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    vp = r.json()["viewer"]
    assert vp["linkedin_url"] == "https://www.linkedin.com/in/testviewer"
    assert vp["photo_url"] == "https://cdn.example/avatars/x.jpg"
    assert vp["twitter_handle"] == "testviewer"
