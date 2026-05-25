"""The reciprocity-notify cron must be wired into main.py's scheduler,
run through the heartbeat wrapper, and write a sync_status heartbeat.

Mirrors tests/test_usage_cron_registration.py exactly.
"""
from unittest.mock import AsyncMock, patch

import pytest

import app.main as main


def test_reciprocity_notify_job_is_scheduled():
    """_reciprocity_notify must be in the scheduler and use an IntervalTrigger."""
    from apscheduler.triggers.interval import IntervalTrigger

    funcs = {j.func for j in main.scheduler.get_jobs()}
    assert main._reciprocity_notify in funcs, (
        "_reciprocity_notify not found in scheduler jobs — did you add it to main.py?"
    )
    job = next(j for j in main.scheduler.get_jobs() if j.func is main._reciprocity_notify)
    # Must use IntervalTrigger, not CronTrigger
    assert isinstance(job.trigger, IntervalTrigger), (
        f"Expected IntervalTrigger, got {type(job.trigger).__name__}"
    )
    # Interval must be 2 hours
    from datetime import timedelta
    assert job.trigger.interval == timedelta(hours=2), (
        f"Expected 2h interval, got {job.trigger.interval}"
    )


@pytest.mark.asyncio
async def test_reciprocity_notify_runs_through_heartbeat():
    """_reciprocity_notify must delegate to _run_with_heartbeat with job_name='reciprocity_notify'."""
    with patch.object(main, "_run_with_heartbeat", AsyncMock()) as hb:
        await main._reciprocity_notify()
    hb.assert_awaited_once()
    assert hb.await_args.args[0] == "reciprocity_notify"


@pytest.mark.asyncio
async def test_reciprocity_notify_calls_both_sub_jobs():
    """The cron factory must call run_interest_notifications then run_mutual_notifications."""
    interest_called = []
    mutual_called = []

    async def _fake_interest(db):
        interest_called.append(True)
        return {"sent": 1, "skipped": 0, "errors": 0}

    async def _fake_mutual(db):
        mutual_called.append(True)
        return {"sent": 2, "skipped": 0, "errors": 0}

    with patch("app.services.interest_cron.run_interest_notifications", _fake_interest), \
         patch("app.services.interest_cron.run_mutual_notifications", _fake_mutual), \
         patch("app.core.database.async_session") as mock_session:
        # Simulate the async context manager that the cron opens
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        # Extract the coro_factory from _run_with_heartbeat and call it directly
        captured_factory = None
        async def _capture_heartbeat(job_name, coro_factory):
            nonlocal captured_factory
            captured_factory = coro_factory
            return await coro_factory()

        with patch.object(main, "_run_with_heartbeat", side_effect=_capture_heartbeat):
            await main._reciprocity_notify()

    assert len(interest_called) == 1, "run_interest_notifications not called"
    assert len(mutual_called) == 1, "run_mutual_notifications not called"
