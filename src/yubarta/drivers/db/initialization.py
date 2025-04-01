from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from yubarta.drivers.db.orm import mapper_registry, start_mappers

from yubarta.conf import settings


class Database:
    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.engine = create_async_engine(db_url, echo=True, future=True)
        self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_database(self):
        """Create all tables defined in the metadata"""
        async with self.engine.begin() as conn:
            await conn.run_sync(mapper_registry.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        """Get a new session for database operations"""
        return self.session_factory()


async def init_database(db_url: str = settings.DATABASE_URL):
    """Initialize the database and return a Database instance"""
    start_mappers()
    db = Database(db_url)
    await db.create_database()
    return db
