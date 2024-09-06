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


class TargetMachine(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str
    username: str
    ssh_key_path: str

    @classmethod
    def create(cls, hostname: str, username: str, ssh_key_path: str) -> "TargetMachine":
        return cls(hostname=hostname, username=username, ssh_key_path=ssh_key_path)


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
