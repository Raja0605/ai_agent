"""
Alembic environment.

Schema was previously created by `Base.metadata.create_all` at startup, which
creates missing tables but never alters existing ones — so any column added
after the first deploy silently never appeared in an existing database.
Migrations own the schema now; create_all remains only as a convenience for a
fresh local run.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Importing every model registers it on Base.metadata so autogenerate can see
# the full schema.
from app.models.application import ApplicationTracking  # noqa: F401
from app.models.job import Job, JobSourceRecord, Skill  # noqa: F401
from app.models.loop import JobLoop, LoopMatch  # noqa: F401
from app.models.user import Resume, User, UserProfile  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The app's configured URL wins, so migrations cannot drift onto another DB.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Needed for SQLite, which cannot ALTER columns in place.
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
