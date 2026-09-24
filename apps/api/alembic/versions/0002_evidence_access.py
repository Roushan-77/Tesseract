"""evidence storage and access workflow

Revision ID: 0002_evidence_access
Revises: 0001_phase_one
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_evidence_access"
down_revision = "0001_phase_one"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("evidence", sa.Column("evidence_id", sa.String(64), nullable=True))
    op.add_column("evidence", sa.Column("mime_type", sa.String(128), nullable=False, server_default="application/octet-stream"))
    op.add_column("evidence", sa.Column("storage_key", sa.String(512), nullable=True))
    op.add_column("evidence", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column("evidence", sa.Column("processing_status", sa.String(32), nullable=False, server_default="UPLOADED"))
    op.add_column("evidence", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("evidence", sa.Column("integrity_status", sa.String(32), nullable=False, server_default="NOT_REGISTERED"))
    op.create_unique_constraint("uq_evidence_storage_key", "evidence", ["storage_key"])
    op.alter_column("evidence", "storage_key", nullable=False)
    op.create_unique_constraint("uq_evidence_evidence_id", "evidence", ["evidence_id"])
    op.alter_column("evidence", "evidence_id", nullable=False)
    op.add_column("access_requests", sa.Column("resource_id", sa.String(64), nullable=True))
    op.add_column("access_requests", sa.Column("reviewed_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True))

def downgrade():
    op.drop_column("access_requests", "reviewed_by_id")
    op.drop_column("access_requests", "resource_id")
    op.drop_constraint("uq_evidence_storage_key", "evidence", type_="unique")
    op.drop_constraint("uq_evidence_evidence_id", "evidence", type_="unique")
    op.drop_column("evidence", "integrity_status")
    op.drop_column("evidence", "notes")
    op.drop_column("evidence", "processing_status")
    op.drop_column("evidence", "updated_at")
    op.drop_column("evidence", "storage_key")
    op.drop_column("evidence", "mime_type")
    op.drop_column("evidence", "evidence_id")
