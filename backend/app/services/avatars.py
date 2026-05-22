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
