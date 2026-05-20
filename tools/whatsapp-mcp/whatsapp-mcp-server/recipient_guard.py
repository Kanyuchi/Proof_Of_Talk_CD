import os
from typing import Optional


def _user_part(recipient: str) -> str:
    r = recipient.strip()
    if "@" in r:
        r = r.split("@", 1)[0]
    if ":" in r:
        r = r.split(":", 1)[0]
    return r


def allowed_recipients() -> Optional[set]:
    raw = os.getenv("WHATSAPP_ALLOWED_JIDS", "").strip()
    if not raw:
        return None  # no restriction
    return {_user_part(j) for j in raw.split(",") if j.strip()}


def is_allowed_recipient(recipient: str) -> bool:
    allowed = allowed_recipients()
    if allowed is None:
        return True
    return _user_part(recipient) in allowed
