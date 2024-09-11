from dataclasses import dataclass, field
from datetime import datetime

from .ebpf import TargetMachine


@dataclass
class ScanResult:
    scanner: "Scanner"
    target_machine: TargetMachine
    data: dict
    scanned_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls, scanner: "Scanner", target_machine: TargetMachine, data: dict
    ) -> "ScanResult":
        return cls(scanner=scanner, target_machine=target_machine, data=data)


@dataclass
class Scanner:
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
