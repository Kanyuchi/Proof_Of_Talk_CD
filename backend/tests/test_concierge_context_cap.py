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


# --- concierge candidate scoping (demo isolation) ------------------------------
from types import SimpleNamespace  # noqa: E402
import uuid as _uuid  # noqa: E402
from app.services.concierge import _scope_candidates  # noqa: E402


def _att(email, name="Pat Doe", company="Acme"):
    return SimpleNamespace(id=_uuid.uuid4(), email=email, name=name, company=company)


def test_demo_viewer_sees_only_other_demo_personas():
    demo1 = _att("amara@demo.proofoftalk.io")
    demo2 = _att("marcus@demo.proofoftalk.io")
    real = _att("ceo@realstartup.com")
    staff = _att("team@proofoftalk.io")
    pool = _scope_candidates([demo1, demo2, real, staff], demo1)
    assert pool == [demo2]  # other demo only — no self, no real, no staff


def test_real_viewer_excludes_demo_and_staff_and_self():
    me = _att("me@acme.com")
    peer = _att("peer@beta.com")
    demo = _att("amara@demo.proofoftalk.io")
    staff = _att("ops@xventures.de")
    pool = _scope_candidates([me, peer, demo, staff], me)
    assert peer in pool
    assert demo not in pool and staff not in pool and me not in pool


def test_no_viewer_defaults_to_real_pool():
    real = _att("a@acme.com")
    demo = _att("x@demo.proofoftalk.io")
    pool = _scope_candidates([real, demo], None)
    assert real in pool and demo not in pool
