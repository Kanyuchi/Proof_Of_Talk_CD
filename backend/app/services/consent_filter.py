"""Consent gate for matching.

High-profile speakers must not appear in the matchmaker until they consent.
Their attendee row carries matching_consent in {pending, declined} until then.
Mirrors the duck-typed accessor style of staff_filter.is_internal_staff so it
works with both ORM Attendee instances and plain dicts.
"""
from typing import Any

GATED_STATES = {"pending", "declined"}


def is_match_gated(attendee: Any) -> bool:
    """True if this attendee is withheld from matching pending/declining consent."""
    if isinstance(attendee, dict):
        val = attendee.get("matching_consent")
    else:
        val = getattr(attendee, "matching_consent", None)
    return (val or "not_required") in GATED_STATES
