from sqlalchemy import JSON, Column, Date, Integer, String, Table
from sqlalchemy.orm import registry

from yubarta.core.models import Alert

mapper_registry = registry()

alerts = Table(
    "alerts",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(255), nullable=False),
    # Column("fingerprint", String(255), nullable=False, index=True),  # Pending to migration
    Column("fingerprint", String(255), nullable=True),
    Column("severity", String(255), nullable=False),
    Column("received_at", Date, nullable=False),
    Column("status_updated_at", Date, nullable=True),
    Column("status", String(255), nullable=False),
    Column("labels", JSON),
    Column("raw", JSON),
)


def start_mappers():
    alerts_mapper = mapper_registry.map_imperatively(Alert, alerts)
