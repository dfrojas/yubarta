"""incident store schema

Revision ID: 9feb26ed05e8
Revises:
Create Date: 2026-07-21 12:15:09.628765

Single revision for the whole incident-store schema. The concurrency columns
(`version`, `lease_owner`, `lease_generation`, `lease_expires_at`) were folded
into this revision by regenerating it rather than stacked as a follow-up:
nothing is deployed, no production data exists, and a second revision would
leave permanent history of a schema that never ran anywhere.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9feb26ed05e8"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("signal_id", sa.String(length=64), nullable=False),
        sa.Column("signal_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("signal_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lease_owner", sa.String(length=255), nullable=True),
        sa.Column("lease_generation", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id"),
    )
    op.create_index("idx_incidents_target_name", "incidents", ["target_name"], unique=False)
    op.create_table(
        "incident_transitions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=False),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_incident_transitions_incident_id", "incident_transitions", ["incident_id"], unique=False)
    op.create_table(
        "remediation_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("remediation_name", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("attempt_sequence", sa.Integer(), nullable=False),
        sa.Column(
            "approval_status",
            sa.String(length=32),
            server_default=sa.text("'not_required'"),
            nullable=False,
        ),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("idx_remediation_attempts_incident_id", "remediation_attempts", ["incident_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_remediation_attempts_incident_id", table_name="remediation_attempts")
    op.drop_table("remediation_attempts")
    op.drop_index("idx_incident_transitions_incident_id", table_name="incident_transitions")
    op.drop_table("incident_transitions")
    op.drop_index("idx_incidents_target_name", table_name="incidents")
    op.drop_table("incidents")
