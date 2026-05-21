from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

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
