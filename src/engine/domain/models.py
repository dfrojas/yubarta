import uuid
from datetime import datetime
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
    ebpf_program: "EBPFProgram"
    target_machine: TargetMachine
    namespace: str
    status: EBPFDeploymentStatus = EBPFDeploymentStatus.PENDING

    @classmethod
    def create(
        cls,
        reference: str,
        ebpf_program: "EBPFProgram",
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


class DetectionResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detector: "Detector"
    scan_result: "ScanResult"
    is_detected: bool
    details: dict
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    # TODO: Add severity

    @classmethod
    def create(
        cls,
        detector: "Detector",
        scan_result: "ScanResult",
        is_detected: bool,
        details: dict,
    ) -> "DetectionResult":
        return cls(
            detector=detector,
            scan_result=scan_result,
            is_detected=is_detected,
            details=details,
        )


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
    def create(cls, name: str, code: str, attach_to: str) -> "Scanner":
        return cls(name=name, code=code, attach_to=attach_to)

    def scan(self, target_machine: TargetMachine) -> "ScanResult":
        # Scanning logic here
        pass


class Detector(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    code: str
    attach_to: str
    detection_criteria: dict  # Define what constitutes a detection

    @classmethod
    def create(cls, name: str, code: str, attach_to: str) -> "Detector":
        return cls(name=name, code=code, attach_to=attach_to)

    def detect(self, scan_result: ScanResult) -> DetectionResult:
        # Detection logic here
        pass


class AlertSeverity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detection_result: DetectionResult
    severity: AlertSeverity
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: str = None
    acknowledged_at: datetime = None


class UserRole(Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"
    VIEWER = "Viewer"


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = None
