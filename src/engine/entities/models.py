from enum import Enum

from pydantic import BaseModel, ConfigDict


class DeploymentStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    FAILED = "Failed"

class TargetMachine(BaseModel):
    hostname: str
    username: str
    ssh_key_path: str = "~/.ssh/id_rsa"
    status: DeploymentStatus = DeploymentStatus.PENDING

    model_config = ConfigDict(frozen=True)

class EBPFProgram(BaseModel):
    name: str
    code: str
    attach_to: str

class EBPFDeployment(BaseModel):
    kind: str
    program: EBPFProgram
    machines: list[TargetMachine]
