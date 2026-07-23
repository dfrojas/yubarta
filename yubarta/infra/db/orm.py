from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import registry

mapper_registry = registry()

incidents = Table(
    "incidents",
    mapper_registry.metadata,
    Column("id", String(64), primary_key=True),
    Column("signal_id", String(64), nullable=False, unique=True),
    Column("signal_fingerprint", String(64), nullable=False),
    Column("signal_raw", JSONB, nullable=False),
    Column("target_name", String(255), nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Index("idx_incidents_target_name", "target_name"),
)

incident_transitions = Table(
    "incident_transitions",
    mapper_registry.metadata,
    Column("id", String(64), primary_key=True),
    Column("incident_id", String(64), ForeignKey("incidents.id"), nullable=False),
    Column("from_state", String(32), nullable=False),
    Column("to_state", String(32), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Index("idx_incident_transitions_incident_id", "incident_id"),
)

remediation_attempts = Table(
    "remediation_attempts",
    mapper_registry.metadata,
    Column("id", String(64), primary_key=True),
    Column("incident_id", String(64), ForeignKey("incidents.id"), nullable=False),
    Column("remediation_name", String(255), nullable=False),
    Column("idempotency_key", String(128), nullable=False, unique=True),
    Column("attempt_sequence", Integer, nullable=False),
    Column("approval_status", String(32), nullable=False, default="not_required"),
    Column("approved_by", String(255), nullable=True),
    Column("approved_at", DateTime(timezone=True), nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("outcome", String(32), nullable=True),
    Column("evidence", JSONB, nullable=True),
    Index("idx_remediation_attempts_incident_id", "incident_id"),
)
