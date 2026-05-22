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
