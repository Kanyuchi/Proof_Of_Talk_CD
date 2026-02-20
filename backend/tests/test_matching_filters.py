"""Tests for deterministic eligibility filters in matching retrieval."""

from types import SimpleNamespace

from app.services.matching import MatchingEngine


def _attendee(**overrides):
    base = {
        "ticket_type": "delegate",
        "not_looking_for": [],
        "preferred_geographies": [],
        "deal_stage": None,
        "seeking": [],
        "intent_tags": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_excludes_candidate_ticket_in_not_looking_for():
    engine = MatchingEngine(db=None)  # db is not used by eligibility helper
    attendee = _attendee(not_looking_for=["speaker"])
    candidate = _attendee(ticket_type="speaker")
    assert engine._is_candidate_eligible(attendee, candidate) is False


def test_excludes_when_geographies_do_not_overlap():
    engine = MatchingEngine(db=None)
    attendee = _attendee(preferred_geographies=["EMEA"])
    candidate = _attendee(preferred_geographies=["APAC"])
    assert engine._is_candidate_eligible(attendee, candidate) is False


def test_excludes_incompatible_policy_and_series_stage():
    engine = MatchingEngine(db=None)
    attendee = _attendee(deal_stage="policy")
    candidate = _attendee(deal_stage="series_b")
    assert engine._is_candidate_eligible(attendee, candidate) is False


def test_excludes_when_seeking_targets_do_not_match():
    engine = MatchingEngine(db=None)
    attendee = _attendee(seeking=["deploying_capital"])
    candidate = _attendee(intent_tags=["knowledge_exchange"], ticket_type="delegate")
    assert engine._is_candidate_eligible(attendee, candidate) is False


def test_allows_when_constraints_are_compatible():
    engine = MatchingEngine(db=None)
    attendee = _attendee(
        ticket_type="vip",
        preferred_geographies=["EMEA", "Middle East"],
        deal_stage="series_b",
        seeking=["raising_capital"],
        intent_tags=["deploying_capital"],
    )
    candidate = _attendee(
        ticket_type="speaker",
        preferred_geographies=["EMEA"],
        deal_stage="series_a_b",
        seeking=["deploying_capital"],
        intent_tags=["raising_capital", "deal_making"],
    )
    assert engine._is_candidate_eligible(attendee, candidate) is True
