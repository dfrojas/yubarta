from sqlalchemy.ext.asyncio import AsyncEngine

from yubarta.drivers.db.orm import Base


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
