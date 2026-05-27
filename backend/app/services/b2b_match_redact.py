"""Row-level transform that masks a b2b counterpart's leaked real name
from stored Match fields. Used by `backend/scripts/redact_b2b_leaks_in_matches.py`
to clean historical rows that pre-date the LLM-side b2b mask shipped on
2026-05-27 (commits 6965805 + 9e6ccbe + 01b1457).

Why a separate module: the daily 03:30 UTC cron only generates matches
for net-new attendees (`refresh_matches_for_new_attendees`), so existing
Match rows never auto-refresh. The LLM-side fixes only prevent NEW leaks.
This module is the cleanup path for everything stored before those fixes.

The actual masking reuses `MatchingEngine._mask_text_for_candidate` so
the same word-boundary semantics apply here as on the LLM prompt side.
"""
from types import SimpleNamespace

from app.services.matching import MatchingEngine


def _wrap(attendee) -> SimpleNamespace:
    """The mask helper uses getattr; wrap dicts so both ORM objects and
    raw dicts work without forking the helper interface."""
    if isinstance(attendee, dict):
        return SimpleNamespace(
            name=attendee.get("name") or "",
            company=attendee.get("company") or "",
            privacy_mode=attendee.get("privacy_mode") or "full",
        )
    return attendee


def redact_b2b_in_match_fields(
    explanation: str | None,
    shared_context: dict | None,
    b2b_attendee,
) -> dict:
    """Return a dict of Match fields that need updating to remove the
    counterpart's real name from stored text. Empty dict means nothing
    to change. Inputs are not mutated.

    Applies the mask to:
      - explanation (top-level string)
      - shared_context['synergies'] / ['action_items'] / ['sectors']
        (each a list of strings)

    Non-string items inside the lists are preserved as-is. The helper
    short-circuits early when the attendee isn't b2b_only or has no name.
    """
    target = _wrap(b2b_attendee)
    if getattr(target, "privacy_mode", "full") != "b2b_only":
        return {}
    name = (getattr(target, "name", None) or "").strip()
    if not name:
        return {}

    changes: dict = {}

    masked_explanation = MatchingEngine._mask_text_for_candidate(explanation, target)
    # Empty input returns "" from the mask; treat that as "no real change"
    # unless the original was also empty - then there's nothing to write.
    original_explanation = explanation or ""
    if masked_explanation != original_explanation:
        changes["explanation"] = masked_explanation

    if isinstance(shared_context, dict):
        cleaned = {**shared_context}
        any_field_changed = False
        for key in ("synergies", "action_items", "sectors"):
            items = cleaned.get(key)
            if not isinstance(items, list):
                continue
            new_items = []
            list_changed = False
            for item in items:
                if not isinstance(item, str):
                    new_items.append(item)
                    continue
                masked_item = MatchingEngine._mask_text_for_candidate(item, target)
                if masked_item != item:
                    list_changed = True
                new_items.append(masked_item)
            if list_changed:
                cleaned[key] = new_items
                any_field_changed = True
        if any_field_changed:
            changes["shared_context"] = cleaned

    return changes
