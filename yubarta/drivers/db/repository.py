from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yubarta.core.models import Alert

# T = TypeVar('T')


class SqlAlchemyAlarmRepository:
    """Repository implementation backed by an *already created* ``AsyncSession``.

    The repository does **not** own the session lifecycle; it simply receives an
    ``AsyncSession`` instance (usually created by a context-manager) and reuses
    it for every operation. This approach allows callers to decide how the
    session is managed (commit/rollback, scoping, etc.) while keeping the
    repository focused on the data-access logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def get_session(self) -> AsyncSession:
        return self._session

    async def add(self, alert: Alert) -> Alert:
        try:
            self._session.add(alert)
            await self._session.commit()
            return alert
        except Exception as e:
            await self._session.rollback()
            raise e

    async def get_all(self) -> list[Alert]:
        query = select(Alert)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    # def search(self, model_class: Type[T], **kwargs: Any) -> List[T]:
    #     return self.get_session().query(model_class).filter_by(**kwargs).all()
