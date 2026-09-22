from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IncidentRow(Base):
    __tablename__ = "incidents"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    target: Mapped[str] = mapped_column(String(512))
    incident_type: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(30))
    version: Mapped[int] = mapped_column(Integer)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_step_id: Mapped[UUID | None] = mapped_column(ForeignKey("incident_steps.id", name="fk_resolving_step", use_alter=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index("uq_active_incident", "target", "incident_type", unique=True, postgresql_where=text("state NOT IN ('RESOLVED', 'FAILED')")),)


class TransitionRow(Base):
    __tablename__ = "incident_state_transitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    from_state: Mapped[str | None] = mapped_column(String(30))
    to_state: Mapped[str] = mapped_column(String(30))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)


class TriggerRow(Base):
    __tablename__ = "trigger_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    source: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw: Mapped[str] = mapped_column(Text)
    normalized: Mapped[dict] = mapped_column(JSONB)


class StepRow(Base):
    __tablename__ = "incident_steps"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_code: Mapped[int | None] = mapped_column(Integer)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("incident_id", "sequence"),)
