from datetime import datetime 
from dataclasses import dataclass
from typing import Optional


@dataclass
class Alert:
    severity: str
    labels: dict
    status: str
    source: str
    raw: dict
    received_at: datetime
    fingerprint: Optional[str] = None
    status_updated_at: Optional[datetime] = None
