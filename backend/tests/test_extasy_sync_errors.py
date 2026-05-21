"""Regression tests for extasy_sync error accounting + observability.

Background — the 2026-05-21 nightly run recorded `errors=58, chunks_failed=1`
in sync_status with NO reason persisted, so PARTIAL was undiagnosable. Root
cause was a single Supabase pooler drop mid-chunk: the per-row `except
Exception` swallowed the connection error for EVERY remaining row in the chunk
(~28 phantom per-row errors on a poisoned session) and then the chunk's commit
failed (+30 chunk-level errors) = 58 from one blip.

These tests pin the two fixes:
  1. A connection-drop error inside the per-row loop must PROPAGATE (so the
     chunk-level handler can retry on a fresh session) — it must NOT be
     counted as a per-row data error.
  2. A genuine per-row data error is counted once AND its reason is recorded
     in the `error_reasons` Counter so the run is diagnosable.
"""

from collections import Counter
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
from sqlalchemy.exc import DBAPIError

from app.services import extasy_sync


def _order(email: str, order_id: str = "o1") -> dict:
    """A minimal valid Extasy order row (one ticket holder)."""
    return {
        "id": order_id,
        "email": email,
        "firstName": "Real",
        "lastName": "Person",
        "ticketNames": "General Pass",
        "status": "PAID",
        "createdAtUtc": "2026-02-12 15:52:44.692113",
        "countryIso3Code": "FRA",
    }


def _connection_dropped_error() -> DBAPIError:
    return DBAPIError.instance(
        statement="SELECT ...",
        params=None,
        orig=asyncpg.exceptions.ConnectionDoesNotExistError(
            "connection was closed in the middle of operation"
        ),
        dbapi_base_err=Exception,
    )


def _fake_db(*, execute_side_effect):
    """A stand-in AsyncSession: begin_nested() is an async CM, execute() is
    driven by the supplied side effect."""
    db = MagicMock()

    @asynccontextmanager
    async def _nested():
        yield SimpleNamespace()

    db.begin_nested = _nested
    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_connection_drop_in_row_loop_propagates_not_swallowed():
    """A pooler drop mid-chunk must bubble up so the caller can retry on a
    fresh session — NOT be miscounted as a per-row data error."""
    db = _fake_db(execute_side_effect=_connection_dropped_error())
    reasons: Counter = Counter()

    with pytest.raises(DBAPIError):
        await extasy_sync._process_order_chunk(
            db, [_order("alice@acme.io")], seen_emails=set(),
            inserted_ids=[], error_reasons=reasons,
        )

    # The connection error was re-raised, not bucketed as a row error.
    assert reasons == Counter()


@pytest.mark.asyncio
async def test_per_row_data_error_is_counted_once_and_reason_recorded():
    """A genuine non-connection error on one row is isolated, counted, and its
    reason recorded so the PARTIAL run is diagnosable."""
    db = _fake_db(execute_side_effect=ValueError("bad enum value"))
    reasons: Counter = Counter()

    stats = await extasy_sync._process_order_chunk(
        db, [_order("bob@acme.io")], seen_emails=set(),
        inserted_ids=[], error_reasons=reasons,
    )

    assert stats["errors"] == 1
    assert stats["inserted"] == 0
    # Reason is bucketed by exception type so repeated failures aggregate.
    assert sum(reasons.values()) == 1
    (reason,) = reasons
    assert reason.startswith("ValueError: bad enum value")
