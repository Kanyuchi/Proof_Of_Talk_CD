"""Tests for matching cache + batching helper behavior."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.matching import MatchingEngine


def _attendee(**overrides):
    base = {
        "id": "a1",
        "embedding": [0.1, 0.2],
        "ticket_type": "delegate",
        "not_looking_for": [],
        "preferred_geographies": [],
        "deal_stage": None,
        "seeking": [],
        "intent_tags": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_retrieve_candidates_uses_warm_cache_without_querying_sql():
    db = AsyncMock()
    engine = MatchingEngine(db=db)
    attendee = _attendee(id="target")
    candidate = _attendee(id="cand")
    engine._candidate_cache["target"] = {
        "items": [{"id": "cand", "similarity": 0.91}],
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    db.get = AsyncMock(return_value=candidate)

    result = await engine.retrieve_candidates(attendee, top_k=1)
    assert len(result) == 1
    assert result[0][0].id == "cand"
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_precompute_candidate_cache_skips_unembedded_attendees():
    db = AsyncMock()
    engine = MatchingEngine(db=db)
    engine.retrieve_candidates = AsyncMock(return_value=[])
    attendees = [_attendee(id="a", embedding=[0.1]), _attendee(id="b", embedding=None)]

    await engine.precompute_candidate_cache(attendees, top_k=5)
    engine.retrieve_candidates.assert_awaited_once()
