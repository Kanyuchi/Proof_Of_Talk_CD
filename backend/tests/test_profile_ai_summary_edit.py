"""PUT /auth/profile accepts `ai_summary` — pins on non-empty, un-pins on empty,
rejects > 2000 chars.

Pattern mirrors tests/test_profile_update.py: TestClient with require_auth + get_db
overridden, a MagicMock attendee whose mutations we inspect directly. We patch
`refresh_profile_matches` (fired via asyncio.create_task) so the test never touches
a real DB / OpenAI.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.api.routes.auth as auth
from app.main import app
from app.core.deps import require_auth
from app.core.database import get_db


def _make_attendee_mock(attendee_id: uuid.UUID) -> MagicMock:
    a = MagicMock()
    a.id = attendee_id
    a.name = "Test Attendee"
    a.email = "test@example.com"
    a.company = "Test Corp"
    a.title = "Founder"
    a.ticket_type = "delegate"
    a.interests = []
    a.goals = None
    a.target_companies = None
    a.seeking = []
    a.not_looking_for = []
    a.preferred_geographies = []
    a.deal_stage = None
    a.photo_url = None
    a.linkedin_url = None
    a.twitter_handle = None
    a.company_website = None
    a.ai_summary = None
    a.ai_summary_pinned = False
    a.ai_summary_edited_at = None
    a.intent_tags = []
    a.vertical_tags = []
    a.deal_readiness_score = None
    a.enriched_profile = {}
    a.privacy_mode = "full"
    a.created_at = datetime(2026, 1, 1)
    a.embedding = None
    return a


def _make_user_mock(attendee_id: uuid.UUID) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test Attendee"
    user.is_admin = False
    user.attendee_id = attendee_id
    return user


def _make_fake_db(attendee):
    db = MagicMock()

    async def fake_get(model, pk):
        return attendee

    db.get = fake_get
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture()
def profile_client():
    attendee_id = uuid.uuid4()
    attendee = _make_attendee_mock(attendee_id)
    user = _make_user_mock(attendee_id)
    fake_db = _make_fake_db(attendee)

    async def _fake_db_gen():
        yield fake_db

    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[require_auth] = lambda: user
    app.dependency_overrides[get_db] = _fake_db_gen

    client = TestClient(app, raise_server_exceptions=False)

    # Stop the fire-and-forget match refresh from touching a real DB / OpenAI.
    with patch.object(auth, "refresh_profile_matches", new=AsyncMock(return_value=None)):
        yield client, attendee

    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


def test_edit_ai_summary_pins(profile_client):
    client, attendee = profile_client
    r = client.put("/api/v1/auth/profile", json={"ai_summary": "My own bio."})
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    assert attendee.ai_summary == "My own bio."
    assert attendee.ai_summary_pinned is True
    assert attendee.ai_summary_edited_at is not None


def test_empty_ai_summary_unpins(profile_client):
    client, attendee = profile_client
    attendee.ai_summary_pinned = True
    r = client.put("/api/v1/auth/profile", json={"ai_summary": "   "})
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    assert attendee.ai_summary_pinned is False


def test_ai_summary_too_long_rejected(profile_client):
    client, attendee = profile_client
    r = client.put("/api/v1/auth/profile", json={"ai_summary": "x" * 2001})
    assert r.status_code == 400
