from datetime import datetime, timezone

from yubarta.domain.signal import Signal, SignalSource, SignalStatus


def normalize_alertmanager(payload: dict) -> list[Signal]:
    signals = []
    for alert in payload.get("alerts", []):
        status = (
            SignalStatus.resolved
            if alert.get("status") == "resolved"
            else SignalStatus.firing
        )
        fired_at = datetime.fromisoformat(alert["startsAt"].replace("Z", "+00:00"))
        signal = Signal(
            status=status,
            source=SignalSource.webhook,
            labels=alert.get("labels", {}),
            fired_at=fired_at,
            raw=alert,
        )
        signals.append(signal)
    return signals
