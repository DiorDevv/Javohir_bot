"""Alembic muhiti (async). DB_URL .env dan olinadi."""
from __future__ import annotations

import asyncio
import logging

from alembic import context
from sqlalchemy.engine import Connection

from bot.config import get_db_url
from bot.db import Base, create_engine
from bot.db.base import is_sqlite

config = context.config
target_metadata = Base.metadata

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")

DB_URL = get_db_url()


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=is_sqlite(DB_URL),
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=is_sqlite(DB_URL),  # SQLite ALTER TABLE cheklovlari uchun
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_engine(DB_URL)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_do_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
