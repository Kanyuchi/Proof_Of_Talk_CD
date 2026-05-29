"""Verify that accepting a match stamps the per-side timestamp exactly once,
and doesn't fire on declined/met transitions.

Uses the mock-DB pattern (SimpleNamespace + AsyncMock) - see test_magic_status.py
and test_adoption_endpoint.py for the canonical approach."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


def _fake_db_for_authed(match):
    """Stub the DB for update_match_status:
    - db.get() returns the match
    - db.commit() and db.refresh() are no-ops
    """
    db = AsyncMock()
    db.get = AsyncMock(return_value=match)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _fake_db_for_magic(attendee, match):
    """Stub the DB for update_match_status_by_magic_link:
    - db.execute() returns the attendee (via scalars().first())
    - db.get() returns the match
    - db.commit() and db.refresh() are no-ops
    """
    class _Scalars:
        def first(self): return attendee
    class _Result:
        def scalars(self): return _Scalars()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.get = AsyncMock(return_value=match)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _fake_match(aid_a, aid_b):
    """A minimal match SimpleNamespace with accepted_*_at = None."""
    return SimpleNamespace(
        id=uuid4(),
        attendee_a_id=aid_a,
        attendee_b_id=aid_b,
        status_a="pending",
        status_b="pending",
        status="pending",
        decline_reason=None,
        accepted_a_at=None,
        accepted_b_at=None,
    )


def _fake_user(attendee_id):
    return SimpleNamespace(attendee_id=attendee_id, is_admin=False)


# --- Test 1: authenticated accept stamps accepted_a_at (A-side) ---

@pytest.mark.asyncio
async def test_accept_stamps_accepted_a_at():
    """Accepting as the A-side user sets accepted_a_at; accepted_b_at stays None."""
    from app.api.routes.matches import update_match_status, MatchStatusUpdate

    aid_a, aid_b = uuid4(), uuid4()
    match = _fake_match(aid_a, aid_b)
    db = _fake_db_for_authed(match)
    user = _fake_user(aid_a)

    with patch("app.api.routes.matches.MatchResponse.model_validate", return_value="ok"):
        await update_match_status(
            match_id=match.id,
            data=MatchStatusUpdate(status="accepted"),
            db=db,
            user=user,
        )

    assert match.accepted_a_at is not None, "accepted_a_at should be stamped on first accept"
    assert isinstance(match.accepted_a_at, datetime)
    assert match.accepted_b_at is None, "accepted_b_at should remain None (B-side hasn't accepted)"


# --- Test 2: authenticated decline does NOT stamp accepted_a_at ---

@pytest.mark.asyncio
async def test_decline_does_not_stamp():
    """Declining as the A-side user must NOT set accepted_a_at."""
    from app.api.routes.matches import update_match_status, MatchStatusUpdate

    aid_a, aid_b = uuid4(), uuid4()
    match = _fake_match(aid_a, aid_b)
    db = _fake_db_for_authed(match)
    user = _fake_user(aid_a)

    with patch("app.api.routes.matches.MatchResponse.model_validate", return_value="ok"):
        await update_match_status(
            match_id=match.id,
            data=MatchStatusUpdate(status="declined", decline_reason="no fit"),
            db=db,
            user=user,
        )

    assert match.accepted_a_at is None, "accepted_a_at must not be stamped on decline"


# --- Test 3: magic-link accept stamps accepted_a_at ---

@pytest.mark.asyncio
async def test_magic_link_accept_stamps_accepted_a_at():
    """Magic-link accept as the A-side attendee sets accepted_a_at."""
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest

    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_a, magic_access_token="tok-abcdef-1234567890")
    match = _fake_match(aid_a, aid_b)
    db = _fake_db_for_magic(attendee, match)

    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )

    assert match.accepted_a_at is not None, "magic-link accept should stamp accepted_a_at"
    assert isinstance(match.accepted_a_at, datetime)


# --- Test 4: second accept call does NOT overwrite the timestamp ---

@pytest.mark.asyncio
async def test_accept_is_idempotent_does_not_overwrite():
    """Second accept call must not bump the timestamp - we record FIRST accept only."""
    from app.api.routes.matches import update_match_status, MatchStatusUpdate

    aid_a, aid_b = uuid4(), uuid4()
    match = _fake_match(aid_a, aid_b)
    user = _fake_user(aid_a)

    # First accept
    db1 = _fake_db_for_authed(match)
    with patch("app.api.routes.matches.MatchResponse.model_validate", return_value="ok"):
        await update_match_status(
            match_id=match.id,
            data=MatchStatusUpdate(status="accepted"),
            db=db1,
            user=user,
        )

    first_ts = match.accepted_a_at
    assert first_ts is not None, "First accept should stamp the timestamp"

    # Second accept - must NOT overwrite first_ts
    db2 = _fake_db_for_authed(match)
    with patch("app.api.routes.matches.MatchResponse.model_validate", return_value="ok"):
        await update_match_status(
            match_id=match.id,
            data=MatchStatusUpdate(status="accepted"),
            db=db2,
            user=user,
        )

    assert match.accepted_a_at == first_ts, (
        "Second accept must not overwrite the original timestamp - idempotency required"
    )
