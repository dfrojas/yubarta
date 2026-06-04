from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from yubarta.config import settings
# from yubarta.infra.db.orm import mapper_registry, start_mappers


class Database:
    def __init__(self, db_uri: str = settings.DATABASE_URI) -> None:
        self.engine = create_async_engine(db_uri, echo=True, future=True)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_database(self) -> None:
        """Create all tables defined in the metadata."""
        print("Creating database")
        # async with self.engine.begin() as conn:
        #     await conn.run_sync(mapper_registry.metadata.create_all)

    # async def get_session(self) -> AsyncSession:
    #     """Get a new session for database operations."""
    #     return self.session_factory()

    # async def close(self) -> None:
    #     """Dispose the underlying engine, freeing any connection pools."""

    #     await self.engine.dispose()


async def init_database(db_url: str = settings.DATABASE_URI) -> Database:
    """Initialize the database and return a ``Database`` instance."""
    # start_mappers()
    db = Database(db_url)
    await db.create_database()
    return db
