from typing import Protocol, TypeVar

from engine.domains import EBPFDeployment, EBPFProgram

T = TypeVar("T")


class AbstractRepository(Protocol):
    def add(self, model: T):
        raise NotImplementedError

    def get(self, reference: str) -> T:
        raise NotImplementedError

    def list(self) -> list[T]:
        raise NotImplementedError


class EBPFDeploymentRepository(AbstractRepository[EBPFDeployment]):
    pass


class EBPFProgramRepository(AbstractRepository[EBPFProgram]):
    pass
