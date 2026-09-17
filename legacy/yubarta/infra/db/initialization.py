from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from yubarta.config import settings
from yubarta.infra.db.unit_of_work import SqlAlchemyUnitOfWork


class Database:
    """Owns the engine and session factory for one process.

    Schema creation is deliberately not here. Migrations run as an explicit
    `alembic upgrade head` step (the `migrate` service in the dev rig, `make migrate`
    by hand), never on application startup: the API is meant to run as more than one
    replica, and several replicas racing to migrate the same database on boot is a
    worse failure than a deploy step that has to be ordered.
    """

    def __init__(self, db_uri: str = settings.DATABASE_URI, echo: bool = False) -> None:
        self.engine = create_async_engine(db_uri, echo=echo, future=True)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    @property
    def unit_of_work(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    async def dispose(self) -> None:
        await self.engine.dispose()
