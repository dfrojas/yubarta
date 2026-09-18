"""Async engine/session helpers. SQLite for tests, PostgreSQL for production."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from yubarta.persistence.models import Base


def resolve_database_url(explicit: str = "") -> str:
    url = explicit or os.environ.get("YUBARTA_DATABASE_URL", "") or "sqlite+aiosqlite:///./yubarta.db"
    return url


def create_engine(url: str, **kwargs: object) -> AsyncEngine:
    options: dict = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    options.update(kwargs)
    return create_async_engine(url, **options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
