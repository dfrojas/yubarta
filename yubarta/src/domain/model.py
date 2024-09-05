from dataclasses import dataclass
from typing import Optional

@dataclass
class EBPFProgram:
    name: str
    code: str
    attach_to: str

@dataclass
class TargetMachine:
    hostname: str
    username: str
    ssh_key_path: str

@dataclass
class EBPFDeployment:
    reference: str
    ebpf_program: EBPFProgram
    target_machine: TargetMachine
    namespace: str
    status: str = "Pending"