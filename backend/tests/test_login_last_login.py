"""POST /auth/login stamps users.last_login_at (throttled, best-effort)."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.api.routes.auth as auth


class _ScalarResult:
    def __init__(self, row):
        self._row = row

    def scalars(self):
        return self

    def first(self):
        return self._row


async def _call_login(db, user):
    """Invoke the undecorated coroutine (bypasses the slowapi limiter)."""
    data = SimpleNamespace(email=user.email, password="pw")
    with patch.object(auth, "verify_password", MagicMock(return_value=True)), \
         patch.object(auth, "create_access_token", MagicMock(return_value="jwt")):
        return await auth.login.__wrapped__(SimpleNamespace(), data, db)


@pytest.mark.asyncio
async def test_login_stamps_last_login_when_null():
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=None,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    out = await _call_login(db, user)
    assert out.access_token == "jwt"
    assert user.last_login_at is not None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_login_throttles_recent_last_login():
    recent = datetime.utcnow() - timedelta(minutes=10)
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=recent,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    await _call_login(db, user)
    # unchanged — inside the 1h throttle window, so no rewrite and no commit
    assert user.last_login_at == recent
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_rewrites_when_older_than_1h():
    old = datetime.utcnow() - timedelta(hours=2)
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=old,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    await _call_login(db, user)
    assert user.last_login_at > old
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_login_hook_failure_does_not_break_response():
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=None,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    db.commit.side_effect = RuntimeError("db down")
    out = await _call_login(db, user)  # must NOT raise
    assert out.access_token == "jwt"


@pytest.mark.asyncio
async def test_login_bad_password_still_401_and_no_stamp():
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=None,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    data = SimpleNamespace(email="a@b.com", password="wrong")
    from fastapi import HTTPException
    with patch.object(auth, "verify_password", MagicMock(return_value=False)):
        with pytest.raises(HTTPException) as ei:
            await auth.login.__wrapped__(SimpleNamespace(), data, db)
    assert ei.value.status_code == 401
    assert user.last_login_at is None
