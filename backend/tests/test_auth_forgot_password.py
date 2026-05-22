"""Regression tests for forgot-password recovery routing.

The pool is ~700 pre-loaded attendees with NO login account. Plain
forgot-password was a silent dead-end for them (it only emails if a User
row exists). It must instead send the magic-link claim ("welcome") email so
they can set a password. These tests pin that branching.
"""

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


async def _run_now(fn, *args, **kwargs):
    """Stand-in for asyncio.to_thread that just calls the (sync) fn."""
    return fn(*args, **kwargs)


async def _call_forgot(db):
    """Invoke the undecorated coroutine (bypasses slowapi limiter) and let
    the fire-and-forget email task drain."""
    import asyncio

    data = SimpleNamespace(email="someone@example.com")
    with patch.object(auth, "send_welcome_email", MagicMock(return_value=True)) as welcome, \
         patch.object(auth, "send_password_reset_email", MagicMock(return_value=True)) as reset, \
         patch.object(auth, "create_reset_token", MagicMock(return_value="tok")), \
         patch("asyncio.to_thread", _run_now):
        out = await auth.forgot_password.__wrapped__(SimpleNamespace(), data, db)
        await asyncio.sleep(0)  # let create_task'd email run
    return out, welcome, reset


@pytest.mark.asyncio
async def test_existing_user_gets_password_reset_not_welcome():
    """A claimed account → real reset email, never the welcome/claim email."""
    user = SimpleNamespace(id="u-1", email="someone@example.com", full_name="Sam")
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)  # User lookup hits

    out, welcome, reset = await _call_forgot(db)

    reset.assert_called_once()
    # force=True so a CLAIMED non-team account (e.g. @xapo.com) can still
    # recover its password while EMAIL_MODE=allowlist — account recovery is
    # transactional and must not be blocked by the team-only allowlist. Mirrors
    # the welcome branch's force. (Regression: Melana Noory, 2026-05-22.)
    _, reset_kwargs = reset.call_args
    assert reset_kwargs.get("force") is True
    welcome.assert_not_called()
    assert "reset link" in out["message"]


@pytest.mark.asyncio
async def test_unclaimed_attendee_gets_magic_link_welcome_email():
    """No User but an attendee row with a magic token → welcome/claim email."""
    attendee = SimpleNamespace(
        email="someone@example.com", name="Tommi", magic_access_token="tok-123"
    )
    db = AsyncMock()
    # 1st execute = User lookup (None), 2nd = Attendee lookup (found)
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(attendee)]

    out, welcome, reset = await _call_forgot(db)

    welcome.assert_called_once()
    _, kwargs = welcome.call_args
    assert kwargs["to_email"] == "someone@example.com"
    assert kwargs["magic_token"] == "tok-123"
    # force=True bypasses the EMAIL_MODE gate so the unclaimed pool can
    # self-recover while bulk automated triggers stay gated on allowlist.
    assert kwargs["force"] is True
    reset.assert_not_called()
    # Response is identical to the user case (no account enumeration).
    assert "reset link" in out["message"]


@pytest.mark.asyncio
async def test_unknown_email_sends_nothing():
    """No User and no attendee → neither email; still the generic message."""
    db = AsyncMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(None)]

    out, welcome, reset = await _call_forgot(db)

    welcome.assert_not_called()
    reset.assert_not_called()
    assert "reset link" in out["message"]


@pytest.mark.asyncio
async def test_attendee_without_token_sends_nothing():
    """Attendee row but no magic token (can't claim) → no email."""
    attendee = SimpleNamespace(email="someone@example.com", name="X", magic_access_token=None)
    db = AsyncMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(attendee)]

    out, welcome, reset = await _call_forgot(db)

    welcome.assert_not_called()
    reset.assert_not_called()


def test_send_password_reset_email_forwards_force_to_send_email():
    """The reset sender must forward `force` to the central _send_email gate so
    the handler's force=True actually bypasses EMAIL_MODE (not just accepted and
    dropped). Default stays force=False."""
    import app.services.email as email_mod

    with patch.object(email_mod, "_send_email", MagicMock(return_value=True)) as se:
        email_mod.send_password_reset_email(
            to_email="a@b.com", user_name="A", reset_token="t", force=True
        )
    assert se.call_args.kwargs.get("force") is True

    with patch.object(email_mod, "_send_email", MagicMock(return_value=True)) as se2:
        email_mod.send_password_reset_email(
            to_email="a@b.com", user_name="A", reset_token="t"
        )
    assert not se2.call_args.kwargs.get("force")
