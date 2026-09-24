"""add evidence integrity records

Revision ID: 0006_integrity
Revises: 0005_multi_format_ingestion
"""
from alembic import op
import sqlalchemy as sa
revision = "0006_integrity"
down_revision = "0005_multi_format_ingestion"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("evidence_integrity",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidence.id"), nullable=False, unique=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("algorithm", sa.String(16), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ledger_record_id", sa.String(128), nullable=False),
        sa.Column("registration_status", sa.String(32), nullable=False),
        sa.Column("verification_status", sa.String(32), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )

def downgrade():
    op.drop_table("evidence_integrity")
