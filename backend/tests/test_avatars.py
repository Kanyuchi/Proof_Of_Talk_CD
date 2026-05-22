import httpx
import pytest
from types import SimpleNamespace
from unittest.mock import Mock

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
