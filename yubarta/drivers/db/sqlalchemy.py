from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yubarta.drivers.db.repository import Repository


class SQLAlchemyUnitOfWork:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self.sessions()
        await self.session.begin()
        self.repository = Repository(self.session)
        return self

    async def __aexit__(self, error_type: object, error: object, traceback: object) -> None:
        try:
            if error_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
