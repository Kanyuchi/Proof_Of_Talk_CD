"""The concierge must cap how many attendees it embeds in the GPT prompt.

Regression for the prod 500: the full ~830-attendee dump produced ~147k tokens
and overflowed GPT-4o's 128k context window. _select_context_attendees caps the
embedded set to MAX_PROMPT_ATTENDEES, preferring the agent-filtered subset.
"""
from app.services.concierge import _select_context_attendees, MAX_PROMPT_ATTENDEES


def _people(n):
    return [object() for _ in range(n)]


def test_caps_full_list_when_no_filter():
    attendees = _people(MAX_PROMPT_ATTENDEES + 500)
    chosen = _select_context_attendees(attendees, [])
    assert len(chosen) == MAX_PROMPT_ATTENDEES


def test_prefers_filtered_subset_and_caps_it():
    attendees = _people(800)
    filtered = attendees[:MAX_PROMPT_ATTENDEES + 30]
    chosen = _select_context_attendees(attendees, filtered)
    assert len(chosen) == MAX_PROMPT_ATTENDEES
    assert chosen == filtered[:MAX_PROMPT_ATTENDEES]  # taken from the filtered set


def test_small_filtered_passes_through_uncapped():
    attendees = _people(800)
    filtered = attendees[:5]
    chosen = _select_context_attendees(attendees, filtered)
    assert chosen == filtered  # 5 relevant people, all kept


def test_cap_is_sane():
    # Far below the ~830 that overflowed; comfortably within 128k tokens.
    assert 20 <= MAX_PROMPT_ATTENDEES <= 200
