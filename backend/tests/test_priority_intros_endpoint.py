# backend/tests/test_priority_intros_endpoint.py
"""GET /matches/priority-intros (authed) and GET /matches/m/{token}/priority-intros
(magic-link) — uses mock-DB pattern (no fixtures, no real DB)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.api.routes.matches as matches_mod


# ---------------------------------------------------------------------------
# Helpers mirroring test_adoption_endpoint.py conventions
# ---------------------------------------------------------------------------

class _Scalar:
    def __init__(self, v):
        self._v = v

    def scalars(self):
        return self

    def first(self):
        return self._v

    def all(self):
        return [self._v] if self._v is not None else []

    def scalar(self):
        return self._v


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


def _make_attendee(**kwargs):
    """Build a SimpleNamespace attendee with all AttendeeResponse-required fields."""
    defaults = dict(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        company="Test Co",
        title=None,
        goals=None,
        interests=[],
        target_companies=None,
        seeking=[],
        not_looking_for=[],
        preferred_geographies=[],
        deal_stage=None,
        linkedin_url=None,
        twitter_handle=None,
        photo_url=None,
        company_website=None,
        privacy_mode="full",
        ticket_type="GENERAL",
        ai_summary=None,
        intent_tags=[],
        vertical_tags=[],
        deal_readiness_score=None,
        enriched_profile={},
        created_at=datetime(2026, 5, 1, 0, 0),
        # Extra fields only on the ORM model (not in schema, but harmless)
        embedding=None,
        magic_access_token=None,
        last_seen_at=None,
        email_opt_out=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_intro(**kwargs):
    """Build a SimpleNamespace RequestedIntro."""
    defaults = dict(
        id=uuid4(),
        requester_attendee_id=uuid4(),
        target_attendee_id=None,
        target_name_raw="Some Person",
        target_company_raw="Some Co",
        source="test",
        added_at=datetime(2026, 5, 28, 12, 0),
        resolved_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_match(**kwargs):
    """Build a SimpleNamespace Match."""
    defaults = dict(
        id=uuid4(),
        attendee_a_id=uuid4(),
        attendee_b_id=uuid4(),
        status="pending",
        status_a="pending",
        status_b="pending",
        overall_score=0.8,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Test 1: authed endpoint returns both resolved AND unresolved intros
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authed_returns_resolved_and_unresolved():
    requester_id = uuid4()
    target_id = uuid4()

    resolved_intro = _make_intro(
        requester_attendee_id=requester_id,
        target_attendee_id=target_id,
        target_name_raw="Resolved Target",
        target_company_raw="Resolved Co",
    )
    unresolved_intro = _make_intro(
        requester_attendee_id=requester_id,
        target_attendee_id=None,
        target_name_raw="Unresolved Person",
        target_company_raw="Unresolved Co",
    )
    target_attendee = _make_attendee(id=target_id, name="Resolved Target", company="Resolved Co")
    match_row = _make_match(attendee_a_id=requester_id, attendee_b_id=target_id)

    db = AsyncMock()
    # Query sequence in _load_priority_intros:
    # 1. select(RequestedIntro) WHERE requester_attendee_id = ...  -> intros
    # 2. select(Attendee) WHERE id IN [target_id]                  -> targets
    # 3. select(Match) WHERE a+b involve target_id                 -> matches
    db.execute.side_effect = [
        _Rows([resolved_intro, unresolved_intro]),   # intros query
        _Rows([target_attendee]),                    # attendee hydration
        _Rows([match_row]),                          # match hydration
    ]

    user = SimpleNamespace(attendee_id=requester_id)
    result = await matches_mod.list_priority_intros(db=db, user=user)

    assert len(result) == 2
    names = {r.target_name_raw for r in result}
    assert "Resolved Target" in names
    assert "Unresolved Person" in names

    # Resolved entry should have target hydrated and match_id set
    resolved = next(r for r in result if r.target_name_raw == "Resolved Target")
    assert resolved.target is not None
    assert resolved.match_id == match_row.id

    # Unresolved entry has no target and no match_id
    unresolved = next(r for r in result if r.target_name_raw == "Unresolved Person")
    assert unresolved.target is None
    assert unresolved.match_id is None


# ---------------------------------------------------------------------------
# Test 2: authed endpoint returns [] when there are no intros
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authed_empty_list_when_no_intros():
    db = AsyncMock()
    db.execute.side_effect = [
        _Rows([]),  # no intros returned
    ]

    user = SimpleNamespace(attendee_id=uuid4())
    result = await matches_mod.list_priority_intros(db=db, user=user)

    assert result == []


# ---------------------------------------------------------------------------
# Test 3: authed endpoint returns [] early when user has no attendee_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authed_no_attendee_id_returns_empty():
    db = AsyncMock()

    user = SimpleNamespace(attendee_id=None)
    result = await matches_mod.list_priority_intros(db=db, user=user)

    assert result == []
    # Must not hit the DB at all
    db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: magic-link returns intros for a valid token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_magic_link_returns_intros_for_valid_token():
    requester_id = uuid4()
    target_id = uuid4()
    token = "a" * 32

    attendee_row = _make_attendee(id=requester_id, magic_access_token=token)
    intro = _make_intro(
        requester_attendee_id=requester_id,
        target_attendee_id=target_id,
        target_name_raw="Priority Target",
        target_company_raw="Priority Co",
    )
    target_attendee = _make_attendee(id=target_id, name="Priority Target")
    match_row = _make_match(attendee_a_id=requester_id, attendee_b_id=target_id)

    db = AsyncMock()
    # Query sequence:
    # 1. select(Attendee) WHERE magic_access_token = token -> attendee_row
    # 2. select(RequestedIntro) WHERE requester_attendee_id = ...  -> intros
    # 3. select(Attendee) WHERE id IN [target_id]                  -> targets
    # 4. select(Match) WHERE a+b involve target_id                 -> matches
    db.execute.side_effect = [
        _Scalar(attendee_row),        # magic token lookup
        _Rows([intro]),               # intros
        _Rows([target_attendee]),     # target hydration
        _Rows([match_row]),           # match hydration
    ]

    result = await matches_mod.list_priority_intros_by_magic_link(token=token, db=db)

    assert len(result) == 1
    assert result[0].target_attendee_id == target_id
    assert result[0].target is not None
    assert result[0].match_id == match_row.id


# ---------------------------------------------------------------------------
# Test 5: magic-link returns 400 for token shorter than 16 chars
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_magic_link_rejects_short_token():
    from fastapi import HTTPException

    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await matches_mod.list_priority_intros_by_magic_link(token="short", db=db)

    assert exc_info.value.status_code == 400
    db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: magic-link returns 404 for valid-length but unknown token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_magic_link_returns_404_for_unknown_token():
    from fastapi import HTTPException

    token = "b" * 32

    db = AsyncMock()
    # Token lookup returns None (no attendee found)
    db.execute.side_effect = [
        _Scalar(None),  # scalars().first() -> None
    ]

    with pytest.raises(HTTPException) as exc_info:
        await matches_mod.list_priority_intros_by_magic_link(token=token, db=db)

    assert exc_info.value.status_code == 404
