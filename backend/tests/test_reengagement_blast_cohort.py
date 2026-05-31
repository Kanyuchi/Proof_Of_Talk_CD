"""Tests for the re-engagement blast cohort + subject picker (pure functions)."""
from app.services.reengagement_blast import RecipientContext, pick_subject


# ── pick_subject ─────────────────────────────────────────────────────────────


def test_subject_with_incoming_interest_uses_reciprocity_hook():
    s = pick_subject(first_name="William", total_matches=16, incoming_interest_count=3)
    assert s == "3 people want to meet you at Proof of Talk"


def test_subject_with_one_incoming_uses_singular():
    s = pick_subject(first_name="Aylin", total_matches=22, incoming_interest_count=1)
    assert s == "1 person wants to meet you at Proof of Talk"


def test_subject_without_incoming_uses_match_count_anchor():
    s = pick_subject(first_name="William", total_matches=16, incoming_interest_count=0)
    assert s == "Your 16 matches at the Louvre, this Tuesday"


def test_subject_zero_matches_returns_none_to_signal_skip():
    s = pick_subject(first_name="William", total_matches=0, incoming_interest_count=0)
    assert s is None


def test_subject_zero_matches_but_incoming_still_skips():
    """Defensive: incoming_interest > 0 should not happen when total_matches=0
    (incoming interest implies a match row exists), but if it does we still skip
    rather than send a hollow email."""
    s = pick_subject(first_name="X", total_matches=0, incoming_interest_count=2)
    assert s is None


# ── RecipientContext ─────────────────────────────────────────────────────────


def test_recipient_context_has_required_fields():
    ctx = RecipientContext(
        attendee_id="00000000-0000-0000-0000-000000000001",
        email="x@y.com",
        first_name="X",
        magic_token="tok",
        total_matches=16,
        incoming_interest_count=2,
        top_matches=[{"name": "Y", "title": "T", "company": "C"}],
    )
    assert ctx.first_name == "X"
    assert ctx.total_matches == 16
    assert len(ctx.top_matches) == 1
