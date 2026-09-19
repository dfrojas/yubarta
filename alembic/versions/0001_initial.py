"""Initial schema: incidents, transitions, trigger events, steps."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("target", sa.String(256), nullable=False),
        sa.Column("incident_type", sa.String(128), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_step_id", sa.String(64), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.create_table(
        "incident_state_transitions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(64), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=False),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.Text(), default=""),
    )
    op.create_table(
        "trigger_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(64), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("source", sa.String(256), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("raw", sa.Text(), nullable=False),
        sa.Column("fields", sa.JSON(), default=dict),
    )
    op.create_table(
        "incident_steps",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(64), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout_excerpt", sa.Text(), nullable=True),
        sa.Column("stderr_excerpt", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), default=dict),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("incident_steps")
    op.drop_table("trigger_events")
    op.drop_table("incident_state_transitions")
    op.drop_table("incidents")
