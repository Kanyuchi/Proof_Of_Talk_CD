"""Profile-photo upload: validate an image and store it in the Supabase
Storage `avatars` bucket via the service-role key. Returns a public URL.

The browser pre-shrinks images to a 512x512 JPEG, but never trust the client:
content-type and size are re-checked here before anything is stored.
"""
from __future__ import annotations

import time

import httpx

from app.core.config import get_settings

BUCKET = "avatars"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB hard cap (post client-shrink)
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class AvatarError(Exception):
    """Raised on invalid upload (bad type / size) or a storage failure."""


def validate_upload(data: bytes, content_type: str) -> None:
    content_type = (content_type or "").strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise AvatarError(f"Unsupported image type: {content_type!r}")
    if not data:
        raise AvatarError("Empty file")
    if len(data) > MAX_BYTES:
        raise AvatarError("File too large (max 2 MB)")


def upload_avatar(attendee_id: str, data: bytes, content_type: str) -> str:
    """Validate + store the image; return a public URL with a cache-buster.

    Deterministic key `{attendee_id}.{ext}` so a re-upload overwrites in place
    (x-upsert). The `?v=` suffix forces clients/CDN to refetch after a replace.
    """
    content_type = (content_type or "").strip().lower()
    validate_upload(data, content_type)
    settings = get_settings()
    base = settings.SUPABASE_URL.rstrip("/")
    key = f"{attendee_id}.{EXT[content_type]}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{base}/storage/v1/object/{BUCKET}/{key}",
                headers=headers,
                content=data,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AvatarError(f"Storage upload failed: {exc}") from exc
    return f"{base}/storage/v1/object/public/{BUCKET}/{key}?v={int(time.time())}"
