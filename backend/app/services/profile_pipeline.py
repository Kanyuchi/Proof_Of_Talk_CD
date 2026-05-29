"""Detached profile-enrichment + match-refresh triggers.

Two functions, run via asyncio.create_task (NOT FastAPI BackgroundTasks —
that holds the request worker through a 10-20s OpenAI/Grid pipeline and 504s
the edge):

- refresh_profile_matches: LIGHT path. Re-embed from the current profile and
  regenerate matches. No re-scraping. Used by every profile save and as
  stages 2-3 of the cold-start join.
- run_full_enrichment: COLD-START path. Grid + website enrichment, then
  refresh_profile_matches. Used by the sponsor join (no enrichment data yet).
"""
import asyncio
import logging
import traceback
import uuid
from weakref import WeakValueDictionary

from sqlalchemy import text as sql_text

from app.core.database import async_session
from app.models.attendee import Attendee
from app.services.matching import MatchingEngine
from app.services.enrichment import EnrichmentService

logger = logging.getLogger(__name__)

# Per-attendee asyncio locks. WeakValueDictionary so locks are GC'd once
# all concurrent callers for an id have released — avoids unbounded growth
# at 1000+ unique attendees. Trade-off: two callers arriving exactly at GC
# time get fresh locks and don't serialize; that's a theoretical hole, not
# a practical one (a Lock held by any caller keeps the entry alive).
_REFRESH_LOCKS: "WeakValueDictionary[uuid.UUID, asyncio.Lock]" = WeakValueDictionary()


def _lock_for(attendee_id: uuid.UUID) -> asyncio.Lock:
    lock = _REFRESH_LOCKS.get(attendee_id)
    if lock is None:
        lock = asyncio.Lock()
        _REFRESH_LOCKS[attendee_id] = lock
    return lock


async def _record_refresh_error(attendee_id: uuid.UUID, exc: Exception) -> None:
    """Surface a refresh_profile_matches failure into sync_status so the
    dashboard can show error counts + most-recent error instead of the
    bug staying invisible in logs. Uses a fresh session because the
    failing session may be poisoned. Best-effort: a failure to record
    must not raise."""
    try:
        async with async_session() as db:
            # Explicit ::text casts are required because asyncpg can't infer
            # the parameter types inside jsonb_build_object's variadic signature
            # (raises IndeterminateDatatypeError otherwise).
            await db.execute(
                sql_text("""
                    INSERT INTO sync_status (job_name, last_run_at, last_status, stats)
                    VALUES (
                        'refresh_profile_matches', NOW(), 'error',
                        jsonb_build_object(
                            'error_count_total', 1,
                            'last_error', CAST(:err AS text),
                            'last_error_type', CAST(:etype AS text),
                            'last_error_attendee_id', CAST(:aid AS text),
                            'last_error_traceback', CAST(:tb AS text)
                        )
                    )
                    ON CONFLICT (job_name) DO UPDATE SET
                        last_run_at = NOW(),
                        last_status = 'error',
                        stats = COALESCE(sync_status.stats, '{}'::jsonb) || jsonb_build_object(
                            'error_count_total',
                                COALESCE((sync_status.stats->>'error_count_total')::int, 0) + 1,
                            'last_error', EXCLUDED.stats->>'last_error',
                            'last_error_type', EXCLUDED.stats->>'last_error_type',
                            'last_error_attendee_id', EXCLUDED.stats->>'last_error_attendee_id',
                            'last_error_traceback', EXCLUDED.stats->>'last_error_traceback'
                        )
                """),
                {
                    "err": f"{type(exc).__name__}: {exc}"[:500],
                    "etype": type(exc).__name__,
                    "aid": str(attendee_id),
                    "tb": traceback.format_exc()[:4000],
                },
            )
            await db.commit()
    except Exception as record_exc:  # noqa: BLE001
        logger.warning(
            "refresh_profile_matches: failed to record error to sync_status: %s",
            record_exc,
        )


def _is_pooler_prep_stmt_race(exc: BaseException) -> bool:
    """True if `exc` (or any cause in its chain) is the pgbouncer x asyncpg
    prepared-statement race. Pattern:
      asyncpg.exceptions.DuplicatePreparedStatementError("...already exists")
      asyncpg.exceptions.InvalidSQLStatementNameError("...does not exist")
    Both bubble up wrapped in sqlalchemy.exc.ProgrammingError. database.py
    auto-sets the cache-size flags to 0 when DATABASE_URL is the :6543
    pooler, but rare races still leak through (e.g. SAVEPOINT statements
    issued by begin_nested() landing on a recycled connection). Retrying
    with a fresh session resolves it deterministically."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        name = type(cur).__name__
        if name in ("DuplicatePreparedStatementError", "InvalidSQLStatementNameError"):
            return True
        # Also match when only the str of the SQLAlchemy wrapper survives.
        msg = str(cur)
        if "DuplicatePreparedStatementError" in msg or "asyncpg_stmt_" in msg:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


async def refresh_profile_matches(attendee_id: uuid.UUID, notify: bool = False) -> None:
    # Per-attendee serialization: two concurrent saves for the same person
    # would otherwise both run the ~5-10s embed + GPT-4o rerank pipeline,
    # doubling cost and risking the (now-guarded) duplicate-match race.
    # Lock is process-local — multi-worker concurrency still falls through
    # to the DB-level unique constraint as the final backstop.
    async with _lock_for(attendee_id):
        last_exc: Exception | None = None
        # One pooler-race retry with a fresh session. The pipeline is
        # idempotent (process_attendee + generate_matches_for_attendee both
        # upsert) so a retried partial run is safe.
        for attempt in (1, 2):
            try:
                async with async_session() as db:
                    engine = MatchingEngine(db)
                    attendee = await db.get(Attendee, attendee_id)
                    if not attendee:
                        return
                    await engine.process_attendee(attendee)
                    # notify defaults False: saves shouldn't spam match emails; callers may opt in.
                    await engine.generate_matches_for_attendee(
                        attendee_id, top_k=10, notify=notify
                    )
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt == 1 and _is_pooler_prep_stmt_race(exc):
                    logger.warning(
                        "refresh_profile_matches: pgbouncer prep-stmt race for %s; retrying with fresh session",
                        attendee_id,
                    )
                    continue
                logger.exception("refresh_profile_matches failed for %s: %s", attendee_id, exc)
                await _record_refresh_error(attendee_id, exc)
                return
        # Safety net: both attempts raised but neither path returned.
        if last_exc is not None:
            logger.exception("refresh_profile_matches failed for %s after retry: %s", attendee_id, last_exc)
            await _record_refresh_error(attendee_id, last_exc)


async def run_full_enrichment(attendee_id: uuid.UUID) -> None:
    try:
        async with async_session() as db:
            attendee = await db.get(Attendee, attendee_id)
            if not attendee:
                return
            try:
                svc = EnrichmentService()
                # enrich_attendee returns a NEW dict; assigning it is required
                # for SQLAlchemy to detect the JSONB change (mutate-and-reassign
                # the same ref is a silent no-op).
                attendee.enriched_profile = await svc.enrich_attendee(attendee)
                await db.commit()
            except Exception:
                logger.exception(
                    "run_full_enrichment: enrich stage failed for %s", attendee_id
                )
    except Exception as exc:
        logger.exception("run_full_enrichment outer failure for %s: %s", attendee_id, exc)
    # Always attempt the embed + match refresh, even if the enrich stage failed.
    await refresh_profile_matches(attendee_id)
