"""
Demo-persona filter for the matching engine.

The only profiles excluded from matching today are the isolated demo/video
personas on @demo.proofoftalk.io (see scripts/seed_demo_profiles.py) — full
fake profiles that match ONLY each other and must never surface in real
attendees' candidate retrieval (both directions), and are excluded from
dashboard counts.

PoT and X Ventures staff (@proofoftalk.io, @xventures.de, @x-ventures.de)
ARE in the matching pool — they participate as ordinary attendees, both
directions. This is a 2026-05-29 change; before that the two domains were
blocked and Zohair/Victor were the only carve-outs.

The function name `is_internal_staff` is preserved for backwards-compat
with callers in matching.py / concierge.py / export_companies_with_people.py;
semantically it now answers "is this a demo persona?".
"""

from typing import Any

INTERNAL_EMAIL_DOMAINS: set[str] = {
    "demo.proofoftalk.io",
}

INTERNAL_COMPANY_PATTERNS: set[str] = set()

ALLOWED_NAMES: set[str] = set()


def is_internal_staff(attendee: Any) -> bool:
    """Return True if this attendee should be excluded from matching.

    Today the only excluded profiles are the @demo.proofoftalk.io demo
    personas. PoT and X Ventures staff are included as ordinary attendees.

    Accepts both ORM Attendee instances and dicts (uses getattr/get).
    """
    def _get(attr: str) -> str:
        if isinstance(attendee, dict):
            return (attendee.get(attr) or "")
        return (getattr(attendee, attr, "") or "")

    name = _get("name").strip().lower()
    if name in ALLOWED_NAMES:
        return False

    email = _get("email").lower()
    if "@" in email:
        domain = email.split("@", 1)[1]
        # @speaker.proofoftalk.io is OK (legitimate external speakers
        # synthesised by the 1000 Minds sync)
        if domain in INTERNAL_EMAIL_DOMAINS:
            return True

    company = _get("company").strip().lower()
    if company in INTERNAL_COMPANY_PATTERNS:
        return True

    return False
