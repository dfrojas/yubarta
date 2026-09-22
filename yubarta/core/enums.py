from enum import Enum


class IncidentState(str, Enum):
    DETECTED = "DETECTED"
    DIAGNOSING = "DIAGNOSING"
    PRECHECKING = "PRECHECKING"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class StepKind(str, Enum):
    DIAGNOSTIC = "diagnostic"
    PRECHECK = "precheck"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"


class StepState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"
