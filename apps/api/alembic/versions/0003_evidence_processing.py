"""persist OCR and extraction results

Revision ID: 0003_evidence_processing
Revises: 0002_evidence_access
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_evidence_processing"
down_revision = "0002_evidence_access"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evidence", sa.Column("ocr_text", sa.Text(), nullable=True))
    op.add_column("evidence", sa.Column("ocr_pages", sa.JSON(), nullable=True))
    op.add_column("evidence", sa.Column("language_confidence", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("extraction_json", sa.JSON(), nullable=True))
    op.add_column("evidence", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("evidence", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("evidence", "processed_at")
    op.drop_column("evidence", "processing_error")
    op.drop_column("evidence", "extraction_json")
    op.drop_column("evidence", "language_confidence")
    op.drop_column("evidence", "ocr_pages")
    op.drop_column("evidence", "ocr_text")