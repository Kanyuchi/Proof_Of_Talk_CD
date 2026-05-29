# backend/tests/test_refresh_error_surfacing.py
"""When refresh_profile_matches throws, the failure must surface to
sync_status so the dashboard shows it instead of the bug being invisible."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

import app.services.profile_pipeline as pp

pytestmark = pytest.mark.asyncio


class _Ctx:
    """Async context manager that yields a given db mock."""
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *a):
        return False


async def test_refresh_error_writes_to_sync_status(monkeypatch):
    aid = uuid.uuid4()

    # First session: raises during process_attendee
    main_db = AsyncMock()
    main_db.get = AsyncMock(side_effect=RuntimeError("simulated openai 429"))

    # Second session: the error-recording session
    err_db = AsyncMock()

    sessions = iter([_Ctx(main_db), _Ctx(err_db)])
    monkeypatch.setattr(pp, "async_session", lambda: next(sessions))

    await pp.refresh_profile_matches(aid)

    # The error-recording session should have run an INSERT into sync_status
    err_db.execute.assert_awaited_once()
    err_db.commit.assert_awaited_once()

    # Inspect the bound parameters of the INSERT call
    call_args = err_db.execute.await_args
    # call_args.args = (stmt, params_dict)
    assert len(call_args.args) >= 2
    params = call_args.args[1]
    assert params["aid"] == str(aid)
    assert "RuntimeError" in params["etype"]
    assert "simulated openai 429" in params["err"]
    assert "RuntimeError" in params["tb"]  # traceback includes the exception class


async def test_refresh_success_does_NOT_write_error_to_sync_status(monkeypatch):
    aid = uuid.uuid4()

    # Successful main session
    main_db = AsyncMock()
    main_db.get = AsyncMock(return_value=object())

    # If a second session is requested, fail the test
    second_used = {"flag": False}

    def session_factory():
        if not hasattr(session_factory, "_called"):
            session_factory._called = True
            return _Ctx(main_db)
        second_used["flag"] = True
        return _Ctx(AsyncMock())

    monkeypatch.setattr(pp, "async_session", session_factory)
    monkeypatch.setattr(pp, "MatchingEngine", lambda db: type("E", (), {
        "process_attendee": AsyncMock(),
        "generate_matches_for_attendee": AsyncMock(),
    })())

    await pp.refresh_profile_matches(aid)

    assert second_used["flag"] is False, "Success path must NOT open an error-recording session"


async def test_record_error_failure_is_swallowed(monkeypatch):
    """If sync_status itself errors, refresh must not bubble it up."""
    aid = uuid.uuid4()

    main_db = AsyncMock()
    main_db.get = AsyncMock(side_effect=RuntimeError("primary failure"))

    err_db = AsyncMock()
    err_db.execute = AsyncMock(side_effect=RuntimeError("sync_status table missing"))

    sessions = iter([_Ctx(main_db), _Ctx(err_db)])
    monkeypatch.setattr(pp, "async_session", lambda: next(sessions))

    # Must not raise
    await pp.refresh_profile_matches(aid)
