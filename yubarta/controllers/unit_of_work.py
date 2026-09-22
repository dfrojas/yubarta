from typing import Protocol, Self

from yubarta.core.interfaces import RepositoryPort


class UnitOfWork(Protocol):
    repository: RepositoryPort

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *args: object) -> None: ...
