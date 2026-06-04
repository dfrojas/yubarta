from sqlalchemy.ext.asyncio import AsyncSession

# TODO(incident-store): rewrite with Signal-based schema once incident-store change is implemented
# T = TypeVar("T")


class SqlAlchemySignalRepository:
    """Placeholder repository. Will be rewritten in incident-store to satisfy domain.ports.SignalStore."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
