"""add multi-format ingestion metadata and provenance

Revision ID: 0005_multi_format_ingestion
Revises: 0004_prompt_four_intelligence
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_multi_format_ingestion"
down_revision = "0004_prompt_four_intelligence"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evidence", sa.Column("ingestion_method", sa.String(32), nullable=False, server_default="document"))
    op.add_column("evidence", sa.Column("pipeline_version", sa.String(32), nullable=False, server_default="prompt4.5"))
    op.add_column("evidence", sa.Column("structured_json", sa.JSON(), nullable=True))
    op.add_column("relations", sa.Column("source_row", sa.Integer(), nullable=True))
    op.add_column("relations", sa.Column("source_fields", sa.JSON(), nullable=True))
    op.add_column("events", sa.Column("source_row", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("source_fields", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("events", "source_fields")
    op.drop_column("events", "source_row")
    op.drop_column("relations", "source_fields")
    op.drop_column("relations", "source_row")
    op.drop_column("evidence", "structured_json")
    op.drop_column("evidence", "pipeline_version")
    op.drop_column("evidence", "ingestion_method")
