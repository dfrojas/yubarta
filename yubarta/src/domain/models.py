from pydantic import BaseModel
from typing import Optional

class EBPFProgram(BaseModel):
    name: str
    code: str
    attach_to: str

class TargetMachine(BaseModel):
    hostname: str
    username: str
    ssh_key_path: str

class EBPFDeployment(BaseModel):
    reference: str
    ebpf_program: EBPFProgram
    target_machine: TargetMachine
    namespace: str
    status: str = "Pending"
