import pytest
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


def test_upload_avatar_puts_bytes_and_returns_public_url(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200
        text = ""
        def raise_for_status(self): pass

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, headers=None, content=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["content"] = content
            return FakeResp()

    monkeypatch.setattr(avatars.httpx, "Client", FakeClient)

    url = avatars.upload_avatar("att-123", b"abc", "image/png")

    assert "/storage/v1/object/avatars/att-123.png" in captured["url"]
    assert captured["headers"]["x-upsert"] == "true"
    assert captured["headers"]["Content-Type"] == "image/png"
    assert captured["content"] == b"abc"
    # public URL with cache-buster
    assert "/storage/v1/object/public/avatars/att-123.png?v=" in url


def test_upload_avatar_raises_on_storage_error(monkeypatch):
    import httpx as _httpx

    def httpx_err():
        return _httpx.HTTPStatusError("400", request=None, response=None)

    class FakeResp:
        status_code = 400
        text = "bad"
        def raise_for_status(self):
            raise httpx_err()

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k): return FakeResp()

    monkeypatch.setattr(avatars.httpx, "Client", FakeClient)
    with pytest.raises(avatars.AvatarError):
        avatars.upload_avatar("att-9", b"abc", "image/jpeg")
