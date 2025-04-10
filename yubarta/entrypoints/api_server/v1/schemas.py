from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AlertIngestionRequest(BaseModel):
    """
    This schema is optional since we're identifying the provider from the raw payload.
    It could be used for documentation purposes or for APIs where the source is known.
    """

    provider: Optional[str] = None
    payload: dict[str, Any]


class AlertReceiptResponse(BaseModel):
    """
    A lightweight response returned immediately when an alert is received.
    This allows for fast response times while processing continues asynchronously.
    """

    alert_id: str
    status: str
    received_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True


class AlertIngestionResponse(BaseModel):
    """
    Full alert representation after processing.
    This would be used for retrieving alert details later.
    """

    id: str
    source: str
    severity: str
    labels: dict
    status: str
    raw: dict
    received_at: datetime
    status_updated_at: Optional[datetime] = None
    fingerprint: Optional[str] = None

    class Config:
        orm_mode = True
