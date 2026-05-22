import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.api.routes.matches as matches


class _ScalarResult:
    def __init__(self, row):
        self._row = row
    def scalars(self):
        return self
    def first(self):
        return self._row


@pytest.mark.asyncio
async def test_magic_profile_save_dispatches_refresh():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(
        id=aid, twitter_handle=None, target_companies=None, photo_url=None,
        privacy_mode="full", linkedin_url=None, goals=None,
        magic_access_token="tok-abcdef1234567890",
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(attendee)
    data = SimpleNamespace(
        twitter_handle=None, target_companies="VCs in DeFi", photo_url=None,
        privacy_mode=None, linkedin_url=None, goals=None,
    )

    def _ct(coro):
        coro.close()
        return MagicMock()

    with patch.object(matches, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", MagicMock(side_effect=_ct)):
        out = await matches.update_profile_via_magic_link(
            "tok-abcdef1234567890", data, db
        )
    assert out == {"status": "updated"}
    refresh.assert_called_once_with(aid)
