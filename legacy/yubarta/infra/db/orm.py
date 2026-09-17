from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    text,
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
    # Optimistic concurrency control: bumped by every accepted transition.
    Column("version", Integer, nullable=False, server_default=text("0")),
    # Fencing token: bumped only when the Director acquires the ownership lease.
    # Deliberately separate from `version`, they guard different races (ADR-0006).
    Column("lease_owner", String(255), nullable=True),
    Column("lease_generation", Integer, nullable=False, server_default=text("0")),
    Column("lease_expires_at", DateTime(timezone=True), nullable=True),
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
    Column("approval_status", String(32), nullable=False, server_default=text("'not_required'")),
    Column("approved_by", String(255), nullable=True),
    Column("approved_at", DateTime(timezone=True), nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("outcome", String(32), nullable=True),
    Column("evidence", JSONB, nullable=True),
    Index("idx_remediation_attempts_incident_id", "incident_id"),
)
