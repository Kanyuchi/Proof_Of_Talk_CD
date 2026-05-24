"""GET /matches/m/{token} stamps attendees.last_seen_at (throttled, best-effort).

Mirrors tests/test_magic_matches_viewer.py: TestClient + dependency_overrides
with a fake DB (no test database in this repo).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

_client = TestClient(app, raise_server_exceptions=False)
_TOKEN = "tok-abcdef-1234567890"


def _make_attendee(**overrides):
    base = dict(
        id=uuid4(), name="Magic User", email="m@example.invalid",
        company="Acme", title="Founder", ticket_type="DELEGATE",
        interests=["defi"], goals="raising", target_companies="a16z",
        seeking=[], not_looking_for=[], preferred_geographies=[],
        deal_stage=None, photo_url=None, linkedin_url=None,
        twitter_handle=None, company_website=None, ai_summary=None,
        intent_tags=[], vertical_tags=[], deal_readiness_score=None,
        enriched_profile={}, privacy_mode="full",
        magic_access_token=_TOKEN, created_at=datetime(2026, 1, 1),
        last_seen_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _override(attendee, *, commit_raises=False, commits=None):
    """Fake DB: 1st execute() = attendee lookup (.scalars().first()),
    2nd = match lookup (.scalars().all() -> []). Records commit calls so the
    test can assert throttle behaviour."""
    class _Scalars:
        def first(self): return attendee
        def all(self): return []

    class _Result:
        def scalars(self): return _Scalars()

    class _FakeDB:
        async def execute(self, *a, **k): return _Result()
        async def commit(self):
            if commits is not None:
                commits.append(1)
            if commit_raises:
                raise RuntimeError("db down")

    async def _dep():
        yield _FakeDB()
    return _dep


def _get():
    return _client.get(f"/api/v1/matches/m/{_TOKEN}")


def test_magic_open_stamps_last_seen_when_null():
    a = _make_attendee(last_seen_at=None)
    commits = []
    app.dependency_overrides[get_db] = _override(a, commits=commits)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 200, r.text
    assert a.last_seen_at is not None
    assert len(commits) == 1


def test_magic_open_throttles_recent():
    recent = datetime.utcnow() - timedelta(minutes=5)
    a = _make_attendee(last_seen_at=recent)
    commits = []
    app.dependency_overrides[get_db] = _override(a, commits=commits)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 200, r.text
    assert a.last_seen_at == recent       # unchanged
    assert commits == []                  # no write inside throttle window


def test_magic_open_rewrites_when_old():
    old = datetime.utcnow() - timedelta(hours=3)
    a = _make_attendee(last_seen_at=old)
    app.dependency_overrides[get_db] = _override(a)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 200, r.text
    assert a.last_seen_at > old


def test_magic_open_hook_failure_does_not_break_response():
    a = _make_attendee(last_seen_at=None)
    app.dependency_overrides[get_db] = _override(a, commit_raises=True)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    # The match list must still render even though the timestamp write failed.
    assert r.status_code == 200, r.text
    assert r.json()["attendee_id"] == str(a.id)
