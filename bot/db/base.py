"""SQLAlchemy async engine va sessiya fabrikasi."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def is_sqlite(db_url: str) -> bool:
    return make_url(db_url).get_backend_name() == "sqlite"


def ensure_sqlite_dir(db_url: str) -> None:
    """SQLite fayli joylashadigan papkani yaratadi (masalan, data/)."""
    url = make_url(db_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_engine(db_url: str, *, echo: bool = False) -> AsyncEngine:
    ensure_sqlite_dir(db_url)
    engine = create_async_engine(db_url, echo=echo, pool_pre_ping=not is_sqlite(db_url))

    if is_sqlite(db_url):
        # SQLite'da tashqi kalitlar (FK) sukut bo'yicha o'chiq
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_fk(dbapi_conn, _record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_pool(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
