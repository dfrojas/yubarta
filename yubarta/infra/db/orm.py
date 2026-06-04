from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String, Table, Text
from sqlalchemy.orm import registry

# Alert removed — replaced by Signal in domain/

mapper_registry = registry()

alerts = Table(
    "alerts",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("external_id", String(255), nullable=False),
    Column("source", String(255), nullable=False),
    Column("title", String(255), nullable=False),
    Column("message", Text, nullable=False),
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

# remediations = Table(
#     "remediations",
#     mapper_registry.metadata,
#     Column("id", Integer, primary_key=True, autoincrement=True),
#     Column("name", String(255), nullable=False, unique=True),
#     Column("description", Text, nullable=True),
#     Column("version", String(50), nullable=False, default="1.0"),
#     Column("created_at", DateTime(timezone=True), nullable=False),
#     Column("updated_at", DateTime(timezone=True), nullable=False),
#     Column("tags", JSON, nullable=False, default=[]),
#     Column("approval_required", Boolean, nullable=False, default=False),
#     Column("auto_approve_if_ai_generated", Boolean, nullable=False, default=False),
#     Column("match_details", JSON, nullable=False, default={}),
#     Column("targets_details", JSON, nullable=False, default={}),
#     Column("connection_details", JSON, nullable=False, default={}),
#     Column("execute_details", JSON, nullable=False, default={}),
#     Column("success_criteria_details", JSON, nullable=False, default={}),
#     Column("ai_details", JSON, nullable=False, default={}),
#     Column("telemetry_details", JSON, nullable=False, default={}),
#     Column("policy_details", JSON, nullable=False, default={}),
# )


# TODO(incident-store): map Signal/Incident to tables once the domain schema is defined
def start_mappers() -> None:
    pass
