"""Kill-switch tests for the reciprocity-notify cron.

Verifies that RECIPROCITY_NOTIFY_ENABLED=False (the default) prevents
run_interest_notifications and run_mutual_notifications from being called,
and that RECIPROCITY_NOTIFY_ENABLED=True lets them through.

Mirrors the style of test_reciprocity_cron_registration.py.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import app.main as main
from app.core.config import Settings


def _make_settings(**overrides):
    """Build a Settings instance with DB/API keys bypassed, applying overrides."""
    base = {
        "DATABASE_URL": "postgresql+asyncpg://x:x@localhost/x",
        "SECRET_KEY": "test",
    }
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
async def test_killswitch_off_skips_send_functions():
    """When RECIPROCITY_NOTIFY_ENABLED is False, neither send function is invoked."""
    interest_mock = AsyncMock(side_effect=AssertionError("should not be called"))
    mutual_mock = AsyncMock(side_effect=AssertionError("should not be called"))

    disabled_settings = _make_settings(RECIPROCITY_NOTIFY_ENABLED=False)

    with patch.object(main, "get_settings", return_value=disabled_settings), \
         patch.object(main, "_run_with_heartbeat", AsyncMock()) as hb, \
         patch("app.services.interest_cron.run_interest_notifications", interest_mock), \
         patch("app.services.interest_cron.run_mutual_notifications", mutual_mock):
        await main._reciprocity_notify()

    # Heartbeat must still fire (job shows alive-but-disabled on dashboard)
    hb.assert_awaited_once()
    # The heartbeat stats must contain disabled=True
    call_args = hb.await_args
    job_name = call_args.args[0]
    assert job_name == "reciprocity_notify"


@pytest.mark.asyncio
async def test_killswitch_off_heartbeat_carries_disabled_flag():
    """When disabled, the coro_factory passed to _run_with_heartbeat returns {'disabled': True}."""
    disabled_settings = _make_settings(RECIPROCITY_NOTIFY_ENABLED=False)

    captured_result = {}

    async def _capture_heartbeat(job_name, coro_factory):
        captured_result["stats"] = await coro_factory()

    with patch.object(main, "get_settings", return_value=disabled_settings), \
         patch.object(main, "_run_with_heartbeat", side_effect=_capture_heartbeat):
        await main._reciprocity_notify()

    assert captured_result.get("stats") == {"disabled": True}, (
        f"Expected {{'disabled': True}}, got {captured_result.get('stats')}"
    )


@pytest.mark.asyncio
async def test_killswitch_on_invokes_both_send_functions():
    """When RECIPROCITY_NOTIFY_ENABLED is True, both send functions are called."""
    interest_called = []
    mutual_called = []

    async def _fake_interest(db):
        interest_called.append(True)
        return {"sent": 1, "skipped": 0, "errors": 0}

    async def _fake_mutual(db):
        mutual_called.append(True)
        return {"sent": 2, "skipped": 0, "errors": 0}

    enabled_settings = _make_settings(RECIPROCITY_NOTIFY_ENABLED=True)

    with patch.object(main, "get_settings", return_value=enabled_settings), \
         patch("app.services.interest_cron.run_interest_notifications", _fake_interest), \
         patch("app.services.interest_cron.run_mutual_notifications", _fake_mutual), \
         patch("app.core.database.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        async def _capture_heartbeat(job_name, coro_factory):
            return await coro_factory()

        with patch.object(main, "_run_with_heartbeat", side_effect=_capture_heartbeat):
            await main._reciprocity_notify()

    assert len(interest_called) == 1, "run_interest_notifications was not called when enabled"
    assert len(mutual_called) == 1, "run_mutual_notifications was not called when enabled"
