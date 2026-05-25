"""The daily check-ins sync must be wired into main.py's scheduler at 02:05 UTC
(right after extasy_sync) and run through the heartbeat wrapper."""

from unittest.mock import AsyncMock, patch

import pytest

import app.main as main


def test_checkins_sync_job_is_scheduled():
    funcs = {j.func for j in main.scheduler.get_jobs()}
    assert main._daily_checkins_sync in funcs, "check-ins sync cron not registered"
    job = next(j for j in main.scheduler.get_jobs() if j.func is main._daily_checkins_sync)
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "2"
    assert fields["minute"] == "5"


@pytest.mark.asyncio
async def test_daily_checkins_sync_runs_through_heartbeat():
    with patch.object(main, "_run_with_heartbeat", AsyncMock()) as hb, \
         patch("app.services.checkins_sync.sync_checkins_to_db", AsyncMock()):
        await main._daily_checkins_sync()
    hb.assert_awaited_once()
    assert hb.await_args.args[0] == "daily_checkins_sync"
