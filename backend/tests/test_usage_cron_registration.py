# backend/tests/test_usage_cron_registration.py
"""The daily usage-snapshot cron must be wired into main.py's scheduler and
run through the heartbeat wrapper (so a silent failure is visible)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.main as main


def test_usage_snapshot_job_is_scheduled():
    funcs = {j.func for j in main.scheduler.get_jobs()}
    assert main._daily_usage_snapshot in funcs, "usage snapshot cron not registered"
    job = next(j for j in main.scheduler.get_jobs() if j.func is main._daily_usage_snapshot)
    # CronTrigger fields expose hour/minute; assert 03:45 UTC.
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "3"
    assert fields["minute"] == "45"


@pytest.mark.asyncio
async def test_daily_usage_snapshot_runs_through_heartbeat():
    with patch.object(main, "_run_with_heartbeat", AsyncMock()) as hb, \
         patch("app.services.usage_snapshot.compute_and_upsert_usage_daily", AsyncMock()):
        await main._daily_usage_snapshot()
    hb.assert_awaited_once()
    assert hb.await_args.args[0] == "daily_usage_snapshot"
