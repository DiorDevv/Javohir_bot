from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db import Base, Employee, create_engine, create_session_pool


@pytest.fixture
async def session_pool() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    pool = create_session_pool(engine)
    async with pool() as session:
        session.add_all(
            [
                Employee(full_name="Kuchkarova Surayyo"),
                Employee(full_name="Arifxodjayeva Ziyoda"),
                Employee(full_name="Yodgorova Xolida"),
            ]
        )
        await session.commit()
    yield pool
    await engine.dispose()


@pytest.fixture
async def session(session_pool: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_pool() as s:
        yield s
