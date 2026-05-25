"""PATCH /matches/m/{token}/status — tokenless accept/decline (reciprocity loop).

Calls the route function directly with fake DB objects, mirroring
tests/test_match_defer.py (no test database in this repo)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


def _fake_db(attendee, match):
    """1st execute() resolves the attendee by token (.scalars().first());
    db.get() returns the match."""
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


@pytest.mark.asyncio
async def test_magic_accept_sets_a_side_and_computes_mutual():
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_a, magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=aid_a, attendee_b_id=aid_b,
        status_a="pending", status_b="accepted", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        out = await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )
    assert match.status_a == "accepted"
    assert match.status == "accepted"   # both sides accepted -> mutual
    assert out == "ok"


@pytest.mark.asyncio
async def test_magic_accept_sets_b_side():
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_b, magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=aid_a, attendee_b_id=aid_b,
        status_a="accepted", status_b="pending", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )
    assert match.status_b == "accepted"
    assert match.status == "accepted"


@pytest.mark.asyncio
async def test_magic_decline_sets_reason():
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_a, magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=aid_a, attendee_b_id=aid_b,
        status_a="pending", status_b="accepted", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="declined", decline_reason="not relevant"),
            db,
        )
    assert match.status_a == "declined"
    assert match.status == "declined"
    assert match.decline_reason == "not relevant"


@pytest.mark.asyncio
async def test_magic_status_rejects_non_owner():
    from fastapi import HTTPException
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    attendee = SimpleNamespace(id=uuid4(), magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=uuid4(), attendee_b_id=uuid4(),
        status_a="pending", status_b="pending", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with pytest.raises(HTTPException) as exc:
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_magic_status_rejects_bad_status():
    from fastapi import HTTPException
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    attendee = SimpleNamespace(id=uuid4(), magic_access_token="tok-abcdef-1234567890")
    db = _fake_db(attendee, SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=uuid4(), status="met"),
            db,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_magic_status_rejects_short_token():
    from fastapi import HTTPException
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    with pytest.raises(HTTPException) as exc:
        await update_match_status_by_magic_link(
            "short", MagicStatusRequest(match_id=uuid4(), status="accepted"), AsyncMock(),
        )
    assert exc.value.status_code == 400
