import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Supabase silently closes idle server-side connections; without pre_ping the
# pool hands out a dead connection and the request 500s intermittently.
# pool_pre_ping validates each connection on checkout, pool_recycle drops them
# before Supabase's idle timeout, and explicit sizing caps how many backend
# connections one worker can hold so a click spike can't exhaust Postgres.
_url = settings.DATABASE_URL
_is_pooler = "pooler.supabase.com" in _url or ":6543" in _url

_connect_args: dict = {}
if _is_pooler:
    # The transaction-mode pooler (pgbouncer) doesn't support the prepared
    # statements asyncpg caches by default — leaving the cache on makes every
    # query fail with "prepared statement does not exist". Must be 0 here.
    _connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    _url,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=_connect_args,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


# Connection-drop errors that are safe to retry with a fresh session. The
# Supabase DIRECT connection (db.<ref>.supabase.co:5432) drops long-held or
# idle connections mid-operation; pool_pre_ping only validates at CHECKOUT,
# so it cannot catch a drop that happens DURING a query or a write that
# follows a long (e.g. 448s) non-DB phase. asyncpg surfaces these as
# ConnectionDoesNotExistError wrapped in DBAPIError, or as
# Operational/InterfaceError.
DB_RETRYABLE_ERRORS = (DBAPIError, OperationalError, InterfaceError)

_T = TypeVar("_T")


async def run_with_db_retry(
    op: Callable[[AsyncSession], Awaitable[_T]],
    *,
    attempts: int = 2,
    backoff_seconds: float = 1.0,
    label: str = "db op",
) -> _T:
    """Run `op` with a FRESH `async_session()` each attempt, retrying on a
    connection-drop error. `op` receives the session and is responsible for
    its own commit; a fresh session is opened per attempt so a poisoned /
    dropped connection on attempt 1 never carries into the retry.

    This mirrors the per-target fresh-session-and-retry pattern in
    `matching.refresh_matches_for_new_attendees`, factored out so the grid
    audit terminal write, match refresh, and any future long-running cron
    can reuse it instead of duplicating try/except.
    """
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with async_session() as session:
                return await op(session)
        except DB_RETRYABLE_ERRORS as exc:
            last_exc = exc
            if attempt == attempts:
                logger.error("%s: connection drop, no retries left: %s", label, exc)
                raise
            logger.warning(
                "%s: connection drop, retrying with fresh session (attempt %d/%d): %s",
                label, attempt, attempts, exc,
            )
            await asyncio.sleep(backoff_seconds)
    # Unreachable: the loop either returns or raises. Guard for type-checkers.
    raise last_exc  # type: ignore[misc]
