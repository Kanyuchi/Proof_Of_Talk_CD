import pytest
from pydantic import ValidationError

from app.schemas.auth import JoinRequest


def test_join_request_rejects_weak_password():
    with pytest.raises(ValidationError):
        JoinRequest(invite_code="x", email="a@b.com", password="weak", name="A")


def test_join_request_rejects_blank_name():
    with pytest.raises(ValidationError):
        JoinRequest(invite_code="x", email="a@b.com", password="Strong1pass", name="   ")


def test_join_request_valid_minimal():
    r = JoinRequest(invite_code="code", email="a@b.com", password="Strong1pass", name="Ann")
    assert r.invite_code == "code"
    assert r.email == "a@b.com"
    assert r.ticket_type == "SPONSOR"


from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import app.api.routes.auth as auth


class _ScalarResult:
    def __init__(self, row):
        self._row = row
    def scalars(self):
        return self
    def first(self):
        return self._row


def _reg_data(**over):
    base = dict(
        email="new@x.com", password="Strong1pass", name="Reg User", company="Co",
        title="CTO", ticket_type="delegate", interests=[], goals=None, seeking=[],
        not_looking_for=[], preferred_geographies=[], deal_stage=None,
        linkedin_url=None, twitter_handle=None, company_website=None,
        privacy_mode="full",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _fake_ct():
    def _ct(coro):
        coro.close()
        return MagicMock()
    return MagicMock(side_effect=_ct)


@pytest.mark.asyncio
async def test_register_dispatches_refresh_profile_matches():
    data = _reg_data()
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(None)]
    ct = _fake_ct()
    with patch.object(auth, "get_settings",
                      lambda: SimpleNamespace(REQUIRE_TICKET_TO_REGISTER=False,
                                              SPONSOR_INVITE_CODE="")), \
         patch.object(auth, "get_password_hash", lambda p: "hashed"), \
         patch.object(auth, "create_access_token", lambda c: "jwt"), \
         patch.object(auth, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", ct):
        out = await auth.register.__wrapped__(SimpleNamespace(), data, None, db)
    assert out.access_token == "jwt"
    refresh.assert_called_once()
    ct.assert_called_once()
