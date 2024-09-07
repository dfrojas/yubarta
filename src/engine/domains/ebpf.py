import uuid
from enum import Enum

from pydantic import BaseModel, Field


class EBPFDeploymentStatus(Enum):
    PENDING = "Pending"
    DEPLOYING = "Deploying"
    DEPLOYED = "Deployed"
    FAILED = "Failed"


class EBPFProgram(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    code: str
    attach_to: str

    @classmethod
    def create(cls, name: str, code: str, attach_to: str) -> "EBPFProgram":
        return cls(name=name, code=code, attach_to=attach_to)


# QUESTION: TargetMachine should be a value object, not a domain object?
class TargetMachine(BaseModel, frozen=True):
    hostname: str
    username: str
    ssh_key_path: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TargetMachine):
            return False
        return (
            self.hostname == other.hostname
            and self.username == other.username
            and self.ssh_key_path == other.ssh_key_path
        )

    def __hash__(self) -> int:
        return hash((self.hostname, self.username, self.ssh_key_path))


class EBPFDeployment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reference: str
    ebpf_program: EBPFProgram
    target_machine: TargetMachine
    namespace: str
    status: EBPFDeploymentStatus = EBPFDeploymentStatus.PENDING

    @classmethod
    def create(
        cls,
        reference: str,
        ebpf_program: EBPFProgram,
        target_machine: TargetMachine,
        namespace: str,
    ) -> "EBPFDeployment":
        return cls(
            reference=reference,
            ebpf_program=ebpf_program,
            target_machine=target_machine,
            namespace=namespace,
        )

    def deploy(self) -> None:
        self.status = EBPFDeploymentStatus.DEPLOYING
        # Deployment logic here
        self.status = EBPFDeploymentStatus.DEPLOYED

    def fail(self) -> None:
        self.status = EBPFDeploymentStatus.FAILED
