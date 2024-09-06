import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .ebpf import TargetMachine


class ScanResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scanner: "Scanner"
    target_machine: TargetMachine
    data: dict
    scanned_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls, scanner: "Scanner", target_machine: TargetMachine, data: dict
    ) -> "ScanResult":
        return cls(scanner=scanner, target_machine=target_machine, data=data)


class Scanner(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    code: str
    attach_to: str
    scan_interval: int  # in seconds
    last_scan: datetime = None

    @classmethod
    def create(
        cls, name: str, code: str, attach_to: str, scan_interval: int
    ) -> "Scanner":
        return cls(
            name=name, code=code, attach_to=attach_to, scan_interval=scan_interval
        )

    def scan(self, target_machine: TargetMachine) -> "ScanResult":
        # Scanning logic here
        pass
