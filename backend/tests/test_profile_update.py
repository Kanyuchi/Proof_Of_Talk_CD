"""TDD regression test for the PUT /auth/profile endpoint.

Root cause: the `allowed` whitelist in `update_profile` was missing
`target_companies`, so "Who do you want to meet?" was silently dropped
on every logged-in profile save.

Pattern: override `require_auth` + `get_db` per-test (snapshot/restore),
consistent with `test_pending_count_route.py`.

Note: We use MagicMock for the Attendee to avoid SQLAlchemy ORM
instrumentation issues when constructing instances outside a session.
The endpoint calls setattr() directly on the object, so MagicMock
captures mutations correctly.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.deps import require_auth
from app.core.database import get_db


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_attendee_mock(attendee_id: uuid.UUID) -> MagicMock:
    """Return a MagicMock that satisfies AttendeeResponse.model_validate.

    We use MagicMock (not a real ORM instance) to avoid SQLAlchemy
    instrumentation errors when constructing objects outside a db session.
    setattr() on a MagicMock stores real values, so the whitelist mutation
    test works correctly.
    """
    attendee = MagicMock()
    attendee.id = attendee_id
    attendee.name = "Test Attendee"
    attendee.email = "test@example.com"
    attendee.company = "Test Corp"
    attendee.title = "Founder"
    attendee.ticket_type = "delegate"
    attendee.interests = []
    attendee.goals = None
    attendee.target_companies = None  # starts as None — the bug drops any write
    attendee.seeking = []
    attendee.not_looking_for = []
    attendee.preferred_geographies = []
    attendee.deal_stage = None
    attendee.photo_url = None
    attendee.linkedin_url = None
    attendee.twitter_handle = None
    attendee.company_website = None
    attendee.ai_summary = None
    attendee.intent_tags = []
    attendee.vertical_tags = []
    attendee.deal_readiness_score = None
    attendee.enriched_profile = {}
    attendee.privacy_mode = "full"
    attendee.created_at = datetime(2026, 1, 1)
    attendee.embedding = None
    return attendee


def _make_user_mock(attendee_id: uuid.UUID) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test Attendee"
    user.is_admin = False
    user.attendee_id = attendee_id
    return user


def _make_fake_db(attendee):
    """Return an async-compatible fake db session."""
    db = MagicMock()

    async def fake_get(model, pk):
        return attendee

    db.get = fake_get
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def profile_client():
    """TestClient with auth + db overridden; cleans up after each test."""
    attendee_id = uuid.uuid4()
    attendee = _make_attendee_mock(attendee_id)
    user = _make_user_mock(attendee_id)
    fake_db = _make_fake_db(attendee)

    async def _fake_db_gen():
        yield fake_db

    # Snapshot existing overrides so we can restore them after the test
    original_overrides = dict(app.dependency_overrides)

    app.dependency_overrides[require_auth] = lambda: user
    app.dependency_overrides[get_db] = _fake_db_gen

    client = TestClient(app, raise_server_exceptions=False)

    # Yield both client and attendee so tests can inspect mutations
    yield client, attendee

    # Restore overrides to avoid cross-test pollution
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_target_companies_is_persisted(profile_client):
    """PUT /profile with target_companies must save the value to the attendee.

    This is the FAILING test before the fix: the whitelist omits
    'target_companies', so setattr is never called and the field stays None.
    """
    client, attendee = profile_client

    resp = client.put(
        "/api/v1/auth/profile",
        json={"target_companies": "Coinbase, a16z crypto"},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert attendee.target_companies == "Coinbase, a16z crypto", (
        f"target_companies not persisted — got {attendee.target_companies!r}"
    )


def test_goals_still_saved_control(profile_client):
    """Control: goals is already whitelisted and must still be saved."""
    client, attendee = profile_client

    resp = client.put(
        "/api/v1/auth/profile",
        json={"goals": "Find Series A investors"},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert attendee.goals == "Find Series A investors", (
        f"goals not persisted — got {attendee.goals!r}"
    )
