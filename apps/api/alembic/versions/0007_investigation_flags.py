"""add investigation flags table

Revision ID: 0007_investigation_flags
Revises: 0006_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_investigation_flags"
down_revision = "0006_integrity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "investigation_flags" not in tables:
        op.create_table(
            "investigation_flags",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
            sa.Column("resource_type", sa.String(32), nullable=False),
            sa.Column("resource_id", sa.String(128), nullable=False),
            sa.Column("resource_label", sa.String(255), nullable=False),
            sa.Column("flagged_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "investigation_flags" in tables:
        op.drop_table("investigation_flags")
