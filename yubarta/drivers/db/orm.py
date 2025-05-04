from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String, Table
from sqlalchemy.orm import registry

from yubarta.core.models import Alert

mapper_registry = registry()

alerts = Table(
    "alerts",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("external_id", String(255), nullable=False),
    Column("source", String(255), nullable=False),
    Column("title", String(255), nullable=False),
    Column("message", String(1023), nullable=False),
    Column("status", String(255), nullable=False),
    Column("severity", String(255), nullable=False),
    Column("scope", String(255), nullable=True),
    Column("tags", JSON, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("fingerprint", String(255), nullable=False),
    Column("enriched", Boolean, nullable=False),
    Column("raw_payload", JSON, nullable=False),
    Index("idx_alerts_fingerprint_occurred_at", "fingerprint", "occurred_at"),
)


def start_mappers() -> None:
    mapper_registry.map_imperatively(Alert, alerts)
