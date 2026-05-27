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
async def test_register_fresh_attendee_dispatches_full_enrichment():
    """A brand-new attendee row (no enriched_at) must trigger the full
    cold-start pipeline — Grid + website enrichment, then re-embed + match
    refresh — so first matches aren't computed from a bare ticket-only
    profile. Mirrors the join-flow contract for the same reason."""
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
         patch.object(auth, "run_full_enrichment", AsyncMock()) as enrich, \
         patch.object(auth, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", ct):
        out = await auth.register.__wrapped__(SimpleNamespace(), data, None, db)
    assert out.access_token == "jwt"
    enrich.assert_called_once()
    refresh.assert_not_called()
    ct.assert_called_once()


@pytest.mark.asyncio
async def test_register_existing_enriched_attendee_dispatches_refresh_only():
    """An attendee row that already has enrichment data (cron picked them up
    yesterday, they're just claiming their account now) should skip the
    expensive cold-start pipeline and only re-embed + refresh matches."""
    from datetime import datetime, timezone
    existing_attendee = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        email="new@x.com",
        name="Existing", company="Existing Co", title="",
        linkedin_url=None, twitter_handle=None, company_website=None,
        goals=None, deal_stage=None, target_companies=None,
        interests=[], seeking=[], not_looking_for=[], preferred_geographies=[],
        privacy_mode="full", ticket_type="delegate",
        magic_access_token="existing-token",
        enriched_at=datetime.now(timezone.utc),
    )
    data = _reg_data()
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(existing_attendee)]
    ct = _fake_ct()
    with patch.object(auth, "get_settings",
                      lambda: SimpleNamespace(REQUIRE_TICKET_TO_REGISTER=True,
                                              SPONSOR_INVITE_CODE="")), \
         patch.object(auth, "get_password_hash", lambda p: "hashed"), \
         patch.object(auth, "create_access_token", lambda c: "jwt"), \
         patch.object(auth, "run_full_enrichment", AsyncMock()) as enrich, \
         patch.object(auth, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", ct):
        out = await auth.register.__wrapped__(SimpleNamespace(), data, None, db)
    assert out.access_token == "jwt"
    refresh.assert_called_once()
    enrich.assert_not_called()


def _join_data(**over):
    base = dict(
        invite_code="secret-code", email="sam@sponsor.com", password="Strong1pass",
        name="Sam Sponsor", company="Acme", title="CEO", interests=[], goals=None,
        target_companies=None, seeking=[], not_looking_for=[],
        preferred_geographies=[], deal_stage=None, linkedin_url=None,
        twitter_handle=None, company_website=None, privacy_mode="full",
        ticket_type="SPONSOR",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _join_settings(code="secret-code"):
    return SimpleNamespace(SPONSOR_INVITE_CODE=code, REQUIRE_TICKET_TO_REGISTER=True)


async def _call_join(data, db, settings):
    with patch.object(auth, "get_settings", lambda: settings), \
         patch.object(auth, "get_password_hash", lambda p: "hashed"), \
         patch.object(auth, "create_access_token", lambda c: "jwt-token"), \
         patch.object(auth, "run_full_enrichment", AsyncMock()) as enrich, \
         patch("asyncio.create_task", _fake_ct()) as ct:
        out = await auth.join.__wrapped__(SimpleNamespace(), data, db)
    return out, enrich, ct


@pytest.mark.asyncio
async def test_join_creates_sponsor_account_and_dispatches_full_enrichment():
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(None)]
    out, enrich, ct = await _call_join(_join_data(), db, _join_settings())
    assert out.access_token == "jwt-token"
    added = [c.args[0] for c in db.add.call_args_list]
    attendee = next(a for a in added if isinstance(a, auth.Attendee))
    assert str(attendee.ticket_type) == "SPONSOR"
    assert attendee.magic_access_token
    enrich.assert_called_once()
    ct.assert_called_once()


@pytest.mark.asyncio
async def test_join_rejects_wrong_code():
    db = AsyncMock()
    with pytest.raises(auth.HTTPException) as exc:
        await _call_join(_join_data(invite_code="wrong"), db, _join_settings())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_join_disabled_when_code_unset():
    db = AsyncMock()
    with pytest.raises(auth.HTTPException) as exc:
        await _call_join(_join_data(), db, _join_settings(code=""))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_join_rejects_existing_user():
    db = AsyncMock()
    db.execute.side_effect = [_ScalarResult(SimpleNamespace(id="u1"))]
    with pytest.raises(auth.HTTPException) as exc:
        await _call_join(_join_data(), db, _join_settings())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_profile_save_dispatches_refresh():
    import uuid
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid, embedding=[1.0], name="X")
    user = SimpleNamespace(attendee_id=aid, full_name="X")
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    ct = _fake_ct()
    with patch.object(auth, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", ct), \
         patch.object(auth, "UserResponse") as UR, \
         patch("app.schemas.attendee.AttendeeResponse") as AR:
        UR.model_validate.return_value = {}
        AR.model_validate.return_value = {}
        await auth.update_profile({"goals": "new goals"}, user, db)
    refresh.assert_called_once_with(aid)
    ct.assert_called_once()


@pytest.mark.asyncio
async def test_join_merges_existing_attendee_and_tags_sponsor():
    existing = SimpleNamespace(
        email="sam@sponsor.com", name="Old", company="Old Co", title="",
        linkedin_url=None, twitter_handle=None, company_website=None, goals=None,
        deal_stage=None, target_companies=None, interests=[], seeking=[],
        not_looking_for=[], preferred_geographies=[], privacy_mode="full",
        magic_access_token=None, ticket_type="DELEGATE", id="att-1",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(existing)]
    out, enrich, ct = await _call_join(
        _join_data(name="New Name", goals="meet VCs"), db, _join_settings()
    )
    assert existing.ticket_type == "SPONSOR"
    assert existing.name == "New Name"
    assert existing.goals == "meet VCs"
    assert existing.magic_access_token
    enrich.assert_called_once()
