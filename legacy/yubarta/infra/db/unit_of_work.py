from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyUnitOfWork:
    """Transaction boundary for Postgres work, and only for Postgres work (ADR-0007).

    Everything executed inside one `begin()` block commits together or not at all.
    A store method never calls `commit()` itself, so "what commits together" is a
    property of this class rather than of whoever happens to hold the session.

    External effects (SSH, HTTP, infrastructure APIs) are never performed inside a
    block: they cannot enlist in a Postgres transaction, and a rollback cannot undo
    them. Record-before-execute is the compensating pattern instead, so the attempt
    row commits before the effect runs and its outcome commits after.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[AsyncSession]:
        session = self._session_factory()
        try:
            # Commits on clean exit, rolls back if the block raises. Reads use it
            # too, so a multi-statement read sees one consistent snapshot.
            async with session.begin():
                yield session
        finally:
            await session.close()
