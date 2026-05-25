"""POST /auth/profile/regenerate-summary returns a fresh AI draft WITHOUT saving
and WITHOUT flipping the pin.

Pattern mirrors tests/test_profile_update.py (TestClient + dependency overrides,
MagicMock attendee). `generate_ai_summary` is imported into auth.py, so we patch
it there.
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
    a.ai_summary = "OLD"
    a.ai_summary_pinned = True
    a.ai_summary_edited_at = None
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
def regen_client():
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
    yield client, attendee, fake_db

    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


def test_regenerate_returns_draft_without_saving(regen_client):
    client, attendee, fake_db = regen_client
    with patch.object(auth, "generate_ai_summary", new=AsyncMock(return_value="FRESH DRAFT")):
        r = client.post("/api/v1/auth/profile/regenerate-summary")
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    assert r.json()["ai_summary"] == "FRESH DRAFT"
    # Not saved; pin unchanged.
    assert attendee.ai_summary == "OLD"
    assert attendee.ai_summary_pinned is True
    fake_db.commit.assert_not_awaited()
