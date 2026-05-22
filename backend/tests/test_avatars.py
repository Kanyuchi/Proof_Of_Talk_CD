import httpx
import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.deps import require_auth
from app.services import avatars


def test_validate_rejects_non_image_content_type():
    with pytest.raises(avatars.AvatarError) as exc:
        avatars.validate_upload(b"hello", "application/pdf")
    assert "type" in str(exc.value).lower()


def test_validate_rejects_oversize():
    big = b"x" * (avatars.MAX_BYTES + 1)
    with pytest.raises(avatars.AvatarError) as exc:
        avatars.validate_upload(big, "image/jpeg")
    assert "large" in str(exc.value).lower() or "size" in str(exc.value).lower()


def test_validate_rejects_empty():
    with pytest.raises(avatars.AvatarError):
        avatars.validate_upload(b"", "image/jpeg")


def test_validate_accepts_png_jpeg_webp():
    for ct in ("image/jpeg", "image/png", "image/webp"):
        avatars.validate_upload(b"some-bytes", ct)  # no raise


def test_validate_accepts_messy_content_type_casing():
    avatars.validate_upload(b"bytes", " Image/JPEG ")  # normalized, no raise


def test_validate_accepts_exact_max_bytes():
    exactly = b"x" * avatars.MAX_BYTES
    assert avatars.validate_upload(exactly, "image/jpeg") is None  # boundary is inclusive


_FAKE_SETTINGS = SimpleNamespace(
    SUPABASE_URL="https://proj.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY="svc-key",
)


@pytest.mark.asyncio
async def test_upload_avatar_puts_bytes_and_returns_public_url(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200
        text = ""
        def raise_for_status(self): pass

    class FakeAsyncClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, content=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["content"] = content
            return FakeResp()

    monkeypatch.setattr(avatars.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(avatars, "get_settings", lambda: _FAKE_SETTINGS)

    url = await avatars.upload_avatar("att-123", b"abc", "image/png")

    assert captured["url"] == "https://proj.supabase.co/storage/v1/object/avatars/att-123.png"
    assert captured["headers"]["x-upsert"] == "true"
    assert captured["headers"]["Content-Type"] == "image/png"
    assert captured["headers"]["apikey"] == "svc-key"
    assert captured["headers"]["Authorization"] == "Bearer svc-key"
    assert captured["content"] == b"abc"
    assert url.startswith(
        "https://proj.supabase.co/storage/v1/object/public/avatars/att-123.png?v="
    )


@pytest.mark.asyncio
async def test_upload_avatar_raises_on_storage_error(monkeypatch):
    class FakeResp:
        status_code = 400
        text = "bad"
        def raise_for_status(self):
            raise httpx.HTTPStatusError("400", request=Mock(), response=Mock())

    class FakeAsyncClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return FakeResp()

    monkeypatch.setattr(avatars.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(avatars, "get_settings", lambda: _FAKE_SETTINGS)

    with pytest.raises(avatars.AvatarError, match="Storage upload failed"):
        await avatars.upload_avatar("att-9", b"abc", "image/jpeg")


# --- magic-link photo endpoint -------------------------------------------------
# Endpoint tests use TestClient + dependency_overrides with a mocked DB (this
# repo has no test database). Pattern mirrors tests/test_pending_count_route.py.
_photo_client = TestClient(app, raise_server_exceptions=False)


def _override_db_returning(attendee):
    class _Scalars:
        def first(self):
            return attendee

    class _Result:
        def scalars(self):
            return _Scalars()

    class _FakeDB:
        async def execute(self, *a, **k):
            return _Result()

        async def commit(self):
            pass

    async def _dep():
        yield _FakeDB()

    return _dep


def test_magic_photo_sets_url_for_token_attendee(monkeypatch):
    attendee = SimpleNamespace(id="att-1", photo_url=None, magic_access_token="tok-abcdef-123456")

    async def _fake_upload(aid, data, ct):
        return "https://example/public/avatars/x.jpg?v=1"

    monkeypatch.setattr("app.api.routes.matches.upload_avatar", _fake_upload)
    app.dependency_overrides[get_db] = _override_db_returning(attendee)
    try:
        r = _photo_client.post(
            "/api/v1/matches/m/tok-abcdef-123456/photo",
            files={"file": ("a.jpg", b"abc", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] == "https://example/public/avatars/x.jpg?v=1"
    assert attendee.photo_url == "https://example/public/avatars/x.jpg?v=1"


def test_magic_photo_404_on_bad_token():
    app.dependency_overrides[get_db] = _override_db_returning(None)
    try:
        r = _photo_client.post(
            "/api/v1/matches/m/not-a-real-token/photo",
            files={"file": ("a.jpg", b"abc", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 404, r.text


def test_magic_photo_400_on_avatar_error(monkeypatch):
    attendee = SimpleNamespace(id="att-1", photo_url=None, magic_access_token="tok-abcdef-123456")

    async def _bad_upload(aid, data, ct):
        raise avatars.AvatarError("Unsupported image type: 'application/pdf'")

    monkeypatch.setattr("app.api.routes.matches.upload_avatar", _bad_upload)
    app.dependency_overrides[get_db] = _override_db_returning(attendee)
    try:
        r = _photo_client.post(
            "/api/v1/matches/m/tok-abcdef-123456/photo",
            files={"file": ("a.pdf", b"abc", "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 400, r.text


def test_magic_photo_400_on_short_token():
    # The len<16 guard rejects before any DB access (no override needed).
    r = _photo_client.post(
        "/api/v1/matches/m/short/photo",
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert r.status_code == 400, r.text


# --- authenticated photo endpoint ----------------------------------------------
@pytest.fixture
def overrides():
    """Snapshot/restore app.dependency_overrides so a test's changes can't leak
    into — or inherit from — other test modules' module-level overrides
    (e.g. test_pending_count_route sets require_auth/get_db at import time)."""
    saved = dict(app.dependency_overrides)
    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def test_auth_photo_requires_jwt(overrides):
    # Remove inherited overrides so the REAL auth dependency runs and fails
    # first (require_auth is declared before get_db). Fixture restores after.
    overrides.pop(require_auth, None)
    overrides.pop(get_db, None)
    r = _photo_client.post(
        "/api/v1/auth/profile/photo",
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert r.status_code in (401, 403), r.text


def test_auth_photo_404_when_no_attendee_linked(overrides):
    # A logged-in user whose account isn't linked to an attendee row.
    overrides[require_auth] = lambda: SimpleNamespace(attendee_id=None)
    r = _photo_client.post(
        "/api/v1/auth/profile/photo",
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert r.status_code == 404, r.text


def test_auth_photo_sets_url_for_logged_in_user(overrides, monkeypatch):
    attendee = SimpleNamespace(id="att-2", photo_url=None)

    async def _fake_upload(aid, data, ct):
        return "https://example/public/avatars/y.jpg?v=2"

    monkeypatch.setattr("app.api.routes.auth.upload_avatar", _fake_upload)

    class _FakeDB:
        async def get(self, model, pk):
            return attendee

        async def commit(self):
            pass

    async def _db_dep():
        yield _FakeDB()

    overrides[get_db] = _db_dep
    overrides[require_auth] = lambda: SimpleNamespace(attendee_id="att-2")

    r = _photo_client.post(
        "/api/v1/auth/profile/photo",
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] == "https://example/public/avatars/y.jpg?v=2"
    assert attendee.photo_url == "https://example/public/avatars/y.jpg?v=2"
