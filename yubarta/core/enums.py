from enum import StrEnum


class IncidentState(StrEnum):
    DETECTED = "DETECTED"
    DIAGNOSING = "DIAGNOSING"
    PRECHECKING = "PRECHECKING"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class StepState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


class StepKind(StrEnum):
    DIAGNOSTIC = "diagnostic"
    PRECHECK = "precheck"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"
