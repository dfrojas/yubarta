from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from yubarta.drivers.db.sqlalchemy import SQLAlchemyUnitOfWork


class Database:
    def __init__(self, url: str):
        self.engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True,
                                                       connect_args={"timeout": 10, "command_timeout": 10})
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    def uow(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self.sessions)

    async def close(self) -> None:
        await self.engine.dispose()
