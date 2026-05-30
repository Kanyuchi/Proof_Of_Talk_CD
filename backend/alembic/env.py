import asyncio
import uuid
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.database import Base
from app.models.attendee import Attendee, Match  # noqa: F401 - ensure models are registered
from app.models.user import User  # noqa: F401
from app.models.message import Conversation, Message  # noqa: F401
from app.models.grid_audit_run import GridAuditRun  # noqa: F401
from app.models.usage_daily import UsageDaily  # noqa: F401

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    # Mirror the pgbouncer-safe connect_args from app.core.database so a
    # migration deploy can't poison server-side prepared-statement state
    # for request-time connections that share the pooler. NullPool keeps
    # each migration command on its own short-lived connection.
    url = config.get_main_option("sqlalchemy.url")
    is_pooler = "pooler.supabase.com" in url or ":6543" in url
    connect_args: dict = {}
    if is_pooler:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = (
            lambda: f"__asyncpg_{uuid.uuid4().hex}__"
        )
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
