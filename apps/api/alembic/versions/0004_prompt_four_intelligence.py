"""add Prompt 4 entity resolution and intelligence records

Revision ID: 0004_prompt_four_intelligence
Revises: 0003_evidence_processing
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_prompt_four_intelligence"
down_revision = "0003_evidence_processing"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("entity_mentions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("mention_key", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("start", sa.Integer(), nullable=False),
        sa.Column("end", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("resolution_status", sa.String(16), nullable=False),
        sa.Column("resolution_confidence", sa.Float()),
        sa.UniqueConstraint("evidence_id", "mention_key", name="uq_entity_mention_evidence_key"),
    )
    op.create_table("entity_resolutions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_mention_id", sa.String(36), sa.ForeignKey("entity_mentions.id"), nullable=False),
        sa.Column("target_mention_id", sa.String(36), sa.ForeignKey("entity_mentions.id"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source_mention_id", "target_mention_id", name="uq_entity_resolution_pair"),
    )
    op.create_table("relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("source_entity_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("target_entity_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("source_mention_id", sa.String(36), sa.ForeignKey("entity_mentions.id"), nullable=False),
        sa.Column("target_mention_id", sa.String(36), sa.ForeignKey("entity_mentions.id"), nullable=False),
        sa.Column("relation_type", sa.String(40), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("evidence_id", "source_mention_id", "target_mention_id", "relation_type", name="uq_relation_provenance"),
    )
    op.create_table("events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("event_key", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_date", sa.String(32)),
        sa.Column("event_time", sa.String(32)),
        sa.Column("location_entity_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("evidence_id", "event_key", name="uq_event_evidence_key"),
    )
    op.create_table("event_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("mention_id", sa.String(36), sa.ForeignKey("entity_mentions.id"), nullable=False),
        sa.UniqueConstraint("event_id", "mention_id", name="uq_event_participant"),
    )


def downgrade():
    op.drop_table("event_participants")
    op.drop_table("events")
    op.drop_table("relations")
    op.drop_table("entity_resolutions")
    op.drop_table("entity_mentions")
    op.drop_table("entities")
