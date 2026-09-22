import json
import re
from datetime import datetime
from typing import Any

from yubarta.config.settings import ParserConfig
from yubarta.core.models import NormalizedEvent


def parse(raw: str, source: str, target: str, config: ParserConfig) -> NormalizedEvent:
    fields: dict[str, Any] = {}
    if config.kind == "json":
        try:
            value = json.loads(raw)
            fields = value if isinstance(value, dict) else {"value": value}
        except json.JSONDecodeError:
            fields = {"parse_error": "Invalid JSON"}
    elif config.kind == "regex":
        match = re.search(config.pattern or "", raw)
        if match:
            fields = match.groupdict()
    timestamp = None
    if value := fields.get("timestamp"):
        try:
            timestamp = datetime.fromisoformat(str(value))
        except ValueError:
            fields["timestamp_parse_error"] = True
    return NormalizedEvent(source=source, target=target, raw=raw,
                           message=str(fields.get("message", raw)),
                           level=str(fields["level"]) if fields.get("level") is not None else None,
                           event_timestamp=timestamp, fields=fields)
