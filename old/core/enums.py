from enum import StrEnum


class AlertStatus(StrEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSource(StrEnum):
    DATADOG = "datadog"
    NEW_RELIC = "new_relic"
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    CUSTOM = "custom"  # From eBPF or custom code injected into the kernel.
