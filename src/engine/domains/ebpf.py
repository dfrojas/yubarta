from dataclasses import dataclass
from enum import Enum

# LEER: https://claude.ai/chat/f88c230e-64fe-4bd9-90c2-64351017d2f7


class EBPFDeploymentStatus(Enum):
    PENDING = "Pending"
    DEPLOYING = "Deploying"
    DEPLOYED = "Deployed"
    FAILED = "Failed"


@dataclass
class EBPFProgram:
    name: str
    code: str
    attach_to: str

    @classmethod
    def create(cls, name: str, code: str, attach_to: str) -> "EBPFProgram":
        return cls(name=name, code=code, attach_to=attach_to)


@dataclass(frozen=True)
class TargetMachine:
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


@dataclass
class EBPFDeployment:
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
