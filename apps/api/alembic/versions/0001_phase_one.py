"""phase one foundation

Revision ID: 0001_phase_one
Revises:
Create Date: 2026-09-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_phase_one"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("investigator_id", sa.String(32), nullable=False, unique=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", sa.String(40), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("cases", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_number", sa.String(32), nullable=False, unique=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("priority", sa.String(32), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("lead_investigator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("case_assignments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("assignment_role", sa.String(40), nullable=False), sa.UniqueConstraint("case_id", "user_id", name="uq_case_assignment"))
    op.create_table("evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("document_type", sa.String(64), nullable=False), sa.Column("document_language", sa.String(16)), sa.Column("uploaded_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ocr_status", sa.String(32), nullable=False), sa.Column("extraction_status", sa.String(32), nullable=False))
    op.create_table("access_requests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("requester_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("reason", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_table("audit_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("action", sa.String(64), nullable=False), sa.Column("resource_type", sa.String(64), nullable=False), sa.Column("resource_id", sa.String(64)), sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id")), sa.Column("result", sa.String(32), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False))

def downgrade():
    op.drop_table("audit_events")
    op.drop_table("access_requests")
    op.drop_table("evidence")
    op.drop_table("case_assignments")
    op.drop_table("cases")
    op.drop_table("users")
