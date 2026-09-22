"""Incident lifecycle and audit timeline."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("target", sa.String(512), nullable=False),
        sa.Column("incident_type", sa.String(200), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by_step_id", sa.Uuid()),
        sa.Column("failure_reason", sa.Text()),
        sa.CheckConstraint("version > 0", name="positive_version"),
        sa.CheckConstraint("state IN ('DETECTED','DIAGNOSING','PRECHECKING','REMEDIATING','VERIFYING','RESOLVED','FAILED')", name="incident_state"),
    )
    op.create_index("uq_active_incident", "incidents", ["target", "incident_type"], unique=True,
                    postgresql_where=sa.text("state NOT IN ('RESOLVED', 'FAILED')"))
    op.create_table("incident_state_transitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("from_state", sa.String(30)),
        sa.Column("to_state", sa.String(30), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
    )
    op.create_table("trigger_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw", sa.Text(), nullable=False),
        sa.Column("normalized", JSONB(), nullable=False),
    )
    op.create_table("incident_steps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("result", JSONB(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.UniqueConstraint("incident_id", "sequence"),
    )
    op.create_foreign_key("fk_resolving_step", "incidents", "incident_steps", ["resolved_by_step_id"], ["id"])
    for table in ["incident_state_transitions", "trigger_events", "incident_steps"]:
        op.create_index(f"ix_{table}_incident_id", table, ["incident_id"])


def downgrade() -> None:
    op.drop_constraint("fk_resolving_step", "incidents", type_="foreignkey")
    for table in ["incident_steps", "trigger_events", "incident_state_transitions", "incidents"]:
        op.drop_table(table)
