# backend/tests/test_matching_priority_intros.py
"""Priority intro requests: in-pool targets get tier upgrade, out-of-pool
targets get force-added with factual explanation (no GPT).

Uses the mock-DB pattern from test_adoption_endpoint.py:
  - Build `db = AsyncMock()` with `db.execute.side_effect` sequenced in the
    exact order the implementation issues queries.
  - Construct in-memory ORM objects; never hit a real database.
"""
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.attendee import Match, RequestedIntro
from app.services.matching import (
    MatchingEngine,
    PRIORITY_INTRO_CAP,
    PRIORITY_INTRO_EXPLANATION_TEMPLATE,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers for constructing in-memory ORM objects without a real DB
# ---------------------------------------------------------------------------

class _Scalar:
    def __init__(self, rows):
        self._rows = rows if isinstance(rows, list) else [rows]

    def scalars(self):
        return self

    def all(self):
        return self._rows

    # Some callers use .first()
    def first(self):
        return self._rows[0] if self._rows else None


def _make_attendee(name="Alice Smith", goals="raise series B", ai_summary=None):
    a = SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        title="CEO",
        company="TestCo",
        goals=goals,
        ai_summary=ai_summary,
        interests=[],
        vertical_tags=[],
        intent_tags=[],
        deal_readiness_score=0.5,
        embedding=[0.1] * 1536,
        enriched_profile={},
        inferred_customer_profile={},
        ticket_type="GA",
        not_looking_for=[],
        preferred_geographies=[],
        deal_stage=None,
        seeking=[],
        privacy_mode="full",
        email="test@example.com",
        email_opt_out=False,
        magic_access_token=None,
        ai_summary_pinned=False,
    )
    return a


def _make_intro(requester_id, target_id, target_name="Target Person", target_company="TargetCo"):
    intro = SimpleNamespace(
        id=uuid.uuid4(),
        requester_attendee_id=requester_id,
        target_attendee_id=target_id,
        target_name_raw=target_name,
        target_company_raw=target_company,
        source="test",
        added_at=datetime.utcnow(),
        resolved_at=None,
    )
    return intro


def _make_match(requester, target, tier="curated"):
    m = Match(
        attendee_a_id=requester.id,
        attendee_b_id=target.id,
        similarity_score=0.85,
        complementary_score=0.85,
        overall_score=0.85,
        match_type="complementary",
        explanation="Test match explanation.",
        shared_context={},
        tier=tier,
    )
    return m


def _make_engine(db):
    engine = MatchingEngine(db)
    return engine


# ---------------------------------------------------------------------------
# Test 1: In-pool match gets tier upgrade to priority_intro
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_in_pool_match_gets_tier_upgrade():
    """When a target is already in existing_matches and they are on the
    requester's priority intro list, their match row's tier must become
    'priority_intro'."""
    requester = _make_attendee(name="Requester")
    target = _make_attendee(name="Target Person")

    intro = _make_intro(requester.id, target.id, target_name=target.name)
    # The existing Match has the target already in pool with tier "curated"
    existing_match = _make_match(requester, target, tier="curated")

    db = AsyncMock()
    # _apply_priority_intros issues one query: SELECT RequestedIntro WHERE ...
    db.execute.side_effect = [
        _Scalar([intro]),   # intros query
        # No second query needed — target is already in existing_matches (no missing_ids)
    ]

    engine = _make_engine(db)
    result = await engine._apply_priority_intros(requester, [existing_match])

    # The match row's tier must be upgraded
    assert existing_match.tier == "priority_intro"
    # The list still contains exactly one match
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Test 2: Out-of-pool target gets force-added
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_out_of_pool_target_force_added():
    """When the target is NOT in existing_matches, a new Match row is appended
    with tier='priority_intro', match_type='priority_intro', all scores 0.0,
    and an explanation built from the template (includes target first name +
    focus)."""
    requester = _make_attendee(name="Requester")
    target = _make_attendee(name="Jane Target", goals="raise series B")
    intro = _make_intro(requester.id, target.id, target_name=target.name)

    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar([intro]),     # intros query
        _Scalar([target]),    # missing attendees query
    ]
    db.add = MagicMock()
    db.flush = AsyncMock()

    engine = _make_engine(db)
    result = await engine._apply_priority_intros(requester, [])

    assert len(result) == 1
    new_match = result[0]
    assert new_match.tier == "priority_intro"
    assert new_match.match_type == "priority_intro"
    assert new_match.similarity_score == 0.0
    assert new_match.complementary_score == 0.0
    assert new_match.overall_score == 0.0
    assert new_match.attendee_a_id == requester.id
    assert new_match.attendee_b_id == target.id
    # Explanation must contain target's first name and focus text
    assert "Jane" in new_match.explanation
    assert "raise series B" in new_match.explanation
    # flush must have been called since we added rows
    db.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 3: Target with NULL target_attendee_id is skipped via SQL filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unresolved_target_attendee_id_null_skipped():
    """The SQL query filters target_attendee_id.is_not(None), so unresolved
    intros never reach the in-memory logic. We verify this by returning an
    empty list from the DB mock (simulating zero rows passing the filter)."""
    requester = _make_attendee(name="Requester")

    db = AsyncMock()
    # Simulate the DB returning zero intros (all had NULL target_attendee_id)
    db.execute.side_effect = [
        _Scalar([]),  # intros query returns nothing
    ]

    engine = _make_engine(db)
    result = await engine._apply_priority_intros(requester, [])

    # No matches added — unresolved intro is invisible to the helper
    assert result == []

    # Confirm the SQL WHERE clause included IS NOT NULL by inspecting the
    # compiled query text
    call_args = db.execute.call_args_list[0]
    stmt = call_args[0][0]  # first positional arg
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "IS NOT NULL" in compiled.upper() or "is_not" in compiled.lower() or "IS NOT" in compiled


# ---------------------------------------------------------------------------
# Test 4: Priority intro cap is enforced at the SQL LIMIT level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_priority_intro_cap_enforced():
    """The SQL query uses .limit(PRIORITY_INTRO_CAP), so only up to CAP rows
    are ever processed regardless of how many RequestedIntro rows exist.
    We verify by introspecting the compiled SQL for the LIMIT clause."""
    requester = _make_attendee(name="Requester")

    db = AsyncMock()
    # Return empty so the helper exits early — we only care about the SQL shape
    db.execute.side_effect = [
        _Scalar([]),  # intros query (empty — all that matters is the SQL)
    ]

    engine = _make_engine(db)
    await engine._apply_priority_intros(requester, [])

    call_args = db.execute.call_args_list[0]
    stmt = call_args[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    # The LIMIT value should be the CAP constant (50)
    assert str(PRIORITY_INTRO_CAP) in compiled
