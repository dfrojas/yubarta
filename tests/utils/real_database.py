"""
Configuration to spin up a real database for __integration__ testing purposes.
"""

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from yubarta.config import settings
from yubarta.drivers.db.orm import mapper_registry


class TestDatabase:
    def __init__(self, db_uri: str = settings.DATABASE_URI):
        self.admin_database_url = (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
        )

    async def setup(self):
        await self.create_test_database()
        self.engine = create_async_engine(settings.DATABASE_URI, echo=True, future=True)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        await self.init_test_db_schema()

    async def override_get_db(self):
        async with self.session_factory() as session:
            yield session

    async def create_test_database(self):
        conn = await asyncpg.connect(self.admin_database_url)
        await conn.execute(f"DROP DATABASE IF EXISTS {settings.DB_NAME} WITH (FORCE)")
        await conn.execute(f"CREATE DATABASE {settings.DB_NAME}")
        await conn.close()

    async def init_test_db_schema(self):
        """Create all tables defined in the metadata"""
        async with self.engine.begin() as conn:
            await conn.run_sync(mapper_registry.metadata.create_all)

    async def drop_test_database(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(mapper_registry.metadata.drop_all)
