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
