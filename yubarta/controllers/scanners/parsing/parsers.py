"""Line parsing: plain text, regex, JSON."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class ParsedLine(BaseModel):
    kind: str = "text"
    message: str
    fields: dict[str, Any] = Field(default_factory=dict)
    level: str | None = None


_LEVEL_PATTERN = re.compile(r"\b(ERROR|WARN(?:ING)?|INFO|DEBUG|CRITICAL|FATAL)\b", re.IGNORECASE)


def parse_line(line: str) -> ParsedLine:
    """Parse one log line as JSON when possible, else regex/plain text."""
    text = line.rstrip("\n")
    if not text.strip():
        return ParsedLine(kind="empty", message=text)
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                message = str(data.get("message", data.get("msg", text)))
                level = data.get("level") or data.get("severity")
                fields = {key: value for key, value in data.items() if key not in ("message", "msg")}
                return ParsedLine(kind="json", message=message, fields=fields, level=str(level) if level else None)
        except json.JSONDecodeError:
            pass
    match = _LEVEL_PATTERN.search(text)
    level = match.group(1).upper() if match else None
    return ParsedLine(kind="text", message=text, level=level)


def matches_any(message: str, patterns: list[str]) -> bool:
    return any(pattern in message for pattern in patterns)


def matches_all(message: str, patterns: list[str]) -> bool:
    return all(pattern in message for pattern in patterns)
