"""Tests for deterministic rerank and confidence scoring helpers."""

from app.models.attendee import Attendee, TicketType
from app.services.matching import MatchingEngine


def _bare_attendee():
    return Attendee(
        name="T", email="t@e.com", company="C", title="T",
        ticket_type=TicketType.DELEGATE, interests=[], goals="",
        enriched_profile={}, intent_tags=[], vertical_tags=[],
    )


def test_deterministic_rerank_penalizes_duplicate_topics_and_sorts():
    engine = MatchingEngine(db=None)
    ranked = [
        {
            "candidate_index": 1,
            "overall_score": 0.80,
            "complementary_score": 0.8,
            "match_type": "complementary",
            "shared_context": {"sectors": ["custody"]},
            "explanation": "A" * 150,
        },
        {
            "candidate_index": 2,
            "overall_score": 0.79,
            "complementary_score": 0.79,
            "match_type": "non_obvious",
            "shared_context": {"sectors": ["custody"]},
            "explanation": "B" * 150,
        },
    ]
    # Empty candidates list skips the vertical/ICP boosts (idx-bounded), so this
    # exercises the duplicate-topic penalty + sort path the test name targets.
    out = engine._deterministic_rerank(ranked, _bare_attendee(), [])
    assert out[0]["overall_score"] >= out[1]["overall_score"]
    assert 0.0 <= out[0]["overall_score"] <= 1.0


def test_confidence_score_is_bounded():
    entry = {
        "overall_score": 0.9,
        "complementary_score": 0.8,
        "explanation": "Strong and specific explanation with concrete detail." * 4,
        "shared_context": {"action_items": ["a", "b", "c"]},
    }
    score = MatchingEngine._estimate_explanation_confidence(entry)
    assert 0.0 <= score <= 1.0
    assert score > 0.6
