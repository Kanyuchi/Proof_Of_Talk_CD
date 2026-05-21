"""Regression tests for the connection-drop resilience of the nightly crons.

Both `daily_grid_audit` and `daily_match_refresh` died nightly with the same
error stored in `sync_status`:

    DBAPIError (asyncpg ConnectionDoesNotExistError):
    connection was closed in the middle of operation

The Supabase DIRECT connection drops long-held / idle connections, and
pool_pre_ping only validates at CHECKOUT — it cannot catch a drop that
happens DURING a query or a write that follows a long non-DB phase (the grid
audit's terminal INSERT runs after ~448s of Grid API calls). The fix is a
shared `run_with_db_retry` helper that opens a FRESH `async_session()` per
attempt and retries once on a connection-drop error.

These tests simulate a `ConnectionDoesNotExistError` on the first attempt and
prove the retry opens a second, fresh session and succeeds.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from sqlalchemy.exc import DBAPIError


def _connection_dropped_error() -> DBAPIError:
    """Build the exact error class the two crons fail with."""
    return DBAPIError.instance(
        statement="INSERT ...",
        params=None,
        orig=asyncpg.exceptions.ConnectionDoesNotExistError(
            "connection was closed in the middle of operation"
        ),
        dbapi_base_err=Exception,
    )


def _flaky_session_factory(sessions: list):
    """Return a callable that mimics `async_session()` — each call yields the
    next prepared session as an async context manager. Lets us hand out a
    'dropped' session first and a healthy one on retry.
    """
    it = iter(sessions)

    def _factory():
        session = next(it)

        @asynccontextmanager
        async def _cm():
            yield session

        return _cm()

    return _factory


@pytest.mark.asyncio
async def test_run_with_db_retry_opens_fresh_session_after_connection_drop():
    """The helper must retry on ConnectionDoesNotExistError with a NEW session."""
    from app.core.database import run_with_db_retry

    dropped = SimpleNamespace(name="dropped")
    healthy = SimpleNamespace(name="healthy")
    factory = _flaky_session_factory([dropped, healthy])

    seen_sessions: list = []

    async def _op(session):
        seen_sessions.append(session)
        if session is dropped:
            raise _connection_dropped_error()
        return "ok"

    with patch("app.core.database.async_session", side_effect=factory), \
         patch("app.core.database.asyncio.sleep", new=AsyncMock()):
        result = await run_with_db_retry(_op, label="test op")

    assert result == "ok"
    # Proves a SECOND, fresh session was used on the retry — not the poisoned one.
    assert seen_sessions == [dropped, healthy]


@pytest.mark.asyncio
async def test_run_with_db_retry_reraises_after_exhausting_attempts():
    """If every attempt drops, the helper must surface the error (cron records it)."""
    from app.core.database import run_with_db_retry

    factory = _flaky_session_factory([SimpleNamespace(), SimpleNamespace()])

    async def _always_drops(session):
        raise _connection_dropped_error()

    with patch("app.core.database.async_session", side_effect=factory), \
         patch("app.core.database.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(DBAPIError):
            await run_with_db_retry(_always_drops, label="test op", attempts=2)


@pytest.mark.asyncio
async def test_grid_audit_terminal_write_survives_connection_drop():
    """grid_audit.persist_audit_run is the terminal INSERT after the ~448s Grid
    loop. A connection dropped during that loop must not lose the run record:
    the write retries on a fresh session and returns the new row id.
    """
    from app.services import grid_audit

    summary = {
        "run_at": "2026-05-21T02:30:00+00:00",
        "duration_seconds": 448.0,
        "total_domains": 10,
        "total_attendees": 25,
        "matched_domains": 6,
        "matched_attendees": 15,
        "had_grid_before_count": 3,
        "new_matches": [{"domain": "x.com", "grid_slug": "x", "grid_name": "X", "sector": "defi"}],
        "unmatched_domains": ["y.com"],
    }

    # First session's commit drops; second session commits cleanly.
    dropped_session = MagicMock()
    dropped_session.add = MagicMock()
    dropped_session.commit = AsyncMock(side_effect=_connection_dropped_error())

    healthy_session = MagicMock()
    healthy_session.add = MagicMock()
    healthy_session.commit = AsyncMock()

    factory = _flaky_session_factory([dropped_session, healthy_session])

    with patch("app.core.database.async_session", side_effect=factory), \
         patch("app.core.database.asyncio.sleep", new=AsyncMock()), \
         patch.object(grid_audit, "GridAuditRun", lambda **kw: SimpleNamespace(id="row-123", **kw)):
        row_id = await grid_audit.persist_audit_run(summary)

    assert row_id == "row-123"
    # The healthy (fresh) session is the one that actually persisted the row.
    healthy_session.add.assert_called_once()
    healthy_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_match_refresh_target_fetch_retries_and_does_not_silently_return_empty():
    """The initial target_ids SELECT used to run on the long-lived cron session;
    on a drop the old code opened a fresh session but never re-ran the SELECT,
    so target_ids stayed empty and the refresh silently produced zero matches.
    The fix re-executes the SELECT on a fresh session, so targets are found.
    """
    from app.services import matching

    target_id = "11111111-1111-1111-1111-111111111111"

    # Target fetch: first session's execute drops, second returns one row.
    dropped_session = MagicMock()
    dropped_session.execute = AsyncMock(side_effect=_connection_dropped_error())

    scalar_result = MagicMock()
    scalar_result.scalars.return_value.all.return_value = [target_id]
    healthy_session = MagicMock()
    healthy_session.execute = AsyncMock(return_value=scalar_result)

    # `async_session` is the SAME object in core.database (used by
    # run_with_db_retry for the target fetch) and in matching's per-target
    # loop, which imports it locally. One factory must serve: drop, healthy
    # (the fetch retry), then unlimited per-target sessions.
    def _factory_with_tail():
        prepared = iter([dropped_session, healthy_session])

        def _make():
            try:
                session = next(prepared)
            except StopIteration:
                session = MagicMock()  # per-target loop sessions

            @asynccontextmanager
            async def _cm():
                yield session

            return _cm()

        return _make

    cron_db = MagicMock()  # long-lived cron session; no longer used for fetch

    fake_engine = MagicMock()
    fake_engine.generate_matches_for_attendee = AsyncMock(return_value=["m1", "m2"])

    with patch("app.core.database.async_session", side_effect=_factory_with_tail()), \
         patch("app.core.database.asyncio.sleep", new=AsyncMock()), \
         patch("app.services.matching.MatchingEngine", return_value=fake_engine):
        result = await matching.refresh_matches_for_new_attendees(cron_db)

    assert result["attendees_processed"] == 1, result
    assert result["matches_created"] == 2, result
    assert result["failed"] == 0, result
    fake_engine.generate_matches_for_attendee.assert_awaited_once()
