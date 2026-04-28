"""
Internal-staff filter for the matching engine.

POT and X Ventures staff are NOT real attendees from the matchmaker's
perspective — they're organisers. They have profiles in the database for
operational reasons (admin accounts, dashboard testing, sponsor outreach
context) but external attendees should never be matched with them.

Exception: Zohair Dehnadi and Victor Blas are X Ventures partners who
use the matchmaker exactly as any external VC would. They stay matchable
in both directions.

This logic was previously duplicated in `scripts/match_sample_report.py`;
this module is the single source of truth.
"""

from typing import Any

INTERNAL_EMAIL_DOMAINS: set[str] = {"proofoftalk.io", "xventures.de", "x-ventures.de"}

INTERNAL_COMPANY_PATTERNS: set[str] = {
    "proof of talk", "proofoftalk", "proof of talk sa",
    "xventures", "x ventures", "x-ventures", "xventures labs",
}

# Names kept matchable despite being on an internal domain.
ALLOWED_NAMES: set[str] = {
    "zohair dehnadi",
    "victor blas",
}


def is_internal_staff(attendee: Any) -> bool:
    """Return True if this attendee is POT/X Ventures organiser staff.

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
