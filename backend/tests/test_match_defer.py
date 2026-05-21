"""Tests for the deep-pool / defer feature: model columns, defer route, deep ranking."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.attendee import Match


def test_match_has_tier_and_deferral_columns():
    m = Match()
    # Defaults are applied at flush time; the attributes must at least exist.
    assert hasattr(m, "tier")
    assert hasattr(m, "deferred_a_at")
    assert hasattr(m, "deferred_b_at")
    # Column metadata is correct.
    cols = Match.__table__.c
    assert cols["tier"].default.arg == "curated"
    assert cols["deferred_a_at"].nullable is True
    assert cols["deferred_b_at"].nullable is True


from app.models.attendee import TicketType


def _attendee(name="Cand", **kw):
    base = dict(
        name=name, email=f"{name.lower()}@e.com", company="C", title="T",
        ticket_type=TicketType.DELEGATE, interests=[], goals="", enriched_profile={},
        intent_tags=[], vertical_tags=[],
    )
    base.update(kw)
    from app.models.attendee import Attendee
    return Attendee(**base)


def test_build_deep_ranked_is_gpt_free_and_templated():
    from app.services.matching import MatchingEngine, DEEP_TIER_EXPLANATION
    engine = MatchingEngine(db=AsyncMock())
    target = _attendee("Target")
    deep = [(_attendee("A"), 0.52), (_attendee("B"), 0.47)]
    ranked = engine._build_deep_ranked(target, deep)
    assert len(ranked) == 2
    assert all(r["explanation"] == DEEP_TIER_EXPLANATION for r in ranked)
    assert all(r["shared_context"].get("tier") == "deep" for r in ranked)
    # candidate_index is 1-based and within range
    assert sorted(r["candidate_index"] for r in ranked) == [1, 2]
