"""Normalized event model shared by scanners and reactors."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class NormalizedEvent(BaseModel):
    source: str
    target: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str
    raw: str
    event_at: datetime | None = None
    level: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)

    def fingerprint(self) -> str:
        import hashlib

        basis = f"{self.source}|{self.target}|{self.message}|{self.raw}"
        return hashlib.sha256(basis.encode()).hexdigest()[:32]
