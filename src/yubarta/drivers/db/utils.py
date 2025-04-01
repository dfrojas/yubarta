from sqlalchemy.ext.asyncio import AsyncSession


async def get_session() -> AsyncSession:
    """FastAPI dependency for database sessions"""
    from yubarta.main import app

    db = app.state.db
    session = await db.get_session()

    try:
        yield session
    finally:
        await session.close()
