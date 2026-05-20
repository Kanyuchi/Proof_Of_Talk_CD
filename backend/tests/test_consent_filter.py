from types import SimpleNamespace
from app.services.consent_filter import is_match_gated


def test_pending_is_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="pending")) is True

def test_declined_is_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="declined")) is True

def test_granted_not_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="granted")) is False

def test_not_required_not_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="not_required")) is False

def test_missing_attr_not_gated():
    assert is_match_gated(SimpleNamespace()) is False

def test_none_value_not_gated():
    assert is_match_gated(SimpleNamespace(matching_consent=None)) is False

def test_dict_form_gated():
    assert is_match_gated({"matching_consent": "pending"}) is True


# Integration test: a pending candidate must be ineligible
from app.services.matching import MatchingEngine


def _make_attendee(**kwargs):
    """Build a minimal stub attendee with all attributes _is_candidate_eligible accesses."""
    defaults = dict(
        matching_consent="not_required",
        name="Test Attendee",
        email="test@external.example.com",
        not_looking_for=[],
        ticket_type="delegate",
        preferred_geographies=[],
        deal_stage=None,
        seeking=[],
        intent_tags=[],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_candidate_eligibility_excludes_gated():
    eng = MatchingEngine.__new__(MatchingEngine)  # no DB needed for this method
    attendee = _make_attendee(matching_consent="not_required", ticket_type="delegate")
    gated = _make_attendee(
        matching_consent="pending",
        ticket_type="speaker",
        name="Stani Kulechov",
        email="stani@external.example.com",
    )
    assert eng._is_candidate_eligible(attendee, gated) is False
