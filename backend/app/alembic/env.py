"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.models import Base

config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def get_database_url() -> str:
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/p2p_db"
    )
    if database_url:
        return database_url

    config_url = config.get_main_option("sqlalchemy.url")
    if config_url:
        return config_url

    return "postgresql+asyncpg://user:password@localhost:5432/p2p_db"


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        get_database_url(),
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
