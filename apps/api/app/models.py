import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def now(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    investigator_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_number: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    lead_investigator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    lead_investigator = relationship("User", foreign_keys=[lead_investigator_id])
    assignments = relationship("CaseAssignment", back_populates="case")

class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    __table_args__ = (UniqueConstraint("case_id", "user_id", name="uq_case_assignment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assignment_role: Mapped[str] = mapped_column(String(40))
    case = relationship("Case", back_populates="assignments")
    user = relationship("User")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_id: Mapped[str] = mapped_column(String(64), unique=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    filename: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    document_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    processing_status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    integrity_status: Mapped[str] = mapped_column(String(32), default="NOT_REGISTERED")
    ocr_status: Mapped[str] = mapped_column(String(32), default="NOT_STARTED")
    extraction_status: Mapped[str] = mapped_column(String(32), default="NOT_STARTED")
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_pages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    language_confidence: Mapped[float | None] = mapped_column(nullable=True)
    extraction_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingestion_method: Mapped[str] = mapped_column(String(32), default="document")
    pipeline_version: Mapped[str] = mapped_column(String(32), default="prompt4.5")
    structured_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    integrity = relationship("EvidenceIntegrity", back_populates="evidence", uselist=False, cascade="all, delete-orphan")
    case = relationship("Case")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    entity_type: Mapped[str] = mapped_column(String(32))
    canonical_name: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    case = relationship("Case")
    mentions = relationship("EntityMentionRecord", back_populates="entity")

class EntityMentionRecord(Base):
    __tablename__ = "entity_mentions"
    __table_args__ = (UniqueConstraint("evidence_id", "mention_key", name="uq_entity_mention_evidence_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"))
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    mention_key: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str] = mapped_column(Text)
    start: Mapped[int] = mapped_column()
    end: Mapped[int] = mapped_column()
    confidence: Mapped[float] = mapped_column()
    resolution_status: Mapped[str] = mapped_column(String(16), default="UNRESOLVED")
    resolution_confidence: Mapped[float | None] = mapped_column(nullable=True)
    evidence = relationship("Evidence")
    entity = relationship("Entity", back_populates="mentions")

class EntityResolution(Base):
    __tablename__ = "entity_resolutions"
    __table_args__ = (UniqueConstraint("source_mention_id", "target_mention_id", name="uq_entity_resolution_pair"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))
    target_mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))
    confidence: Mapped[float] = mapped_column()
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="SUGGESTED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Relation(Base):
    __tablename__ = "relations"
    __table_args__ = (UniqueConstraint("evidence_id", "source_mention_id", "target_mention_id", "relation_type", name="uq_relation_provenance"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"))
    source_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    source_mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))
    target_mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))
    relation_type: Mapped[str] = mapped_column(String(40))
    source_text: Mapped[str] = mapped_column(Text)
    source_row: Mapped[int | None] = mapped_column(nullable=True)
    source_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column()
    observed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("evidence_id", "event_key", name="uq_event_evidence_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"))
    event_key: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(32))
    event_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    source_text: Mapped[str] = mapped_column(Text)
    source_row: Mapped[int | None] = mapped_column(nullable=True)
    source_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class EventParticipant(Base):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "mention_id", name="uq_event_participant"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    mention_id: Mapped[str] = mapped_column(ForeignKey("entity_mentions.id"))

class EvidenceIntegrity(Base):
    __tablename__ = "evidence_integrity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column()
    algorithm: Mapped[str] = mapped_column(String(16), default="SHA-256")
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ledger_record_id: Mapped[str] = mapped_column(String(128))
    registration_status: Mapped[str] = mapped_column(String(32), default="REGISTERED")
    verification_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence = relationship("Evidence", back_populates="integrity")

class AccessRequest(Base):
    __tablename__ = "access_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    result: Mapped[str] = mapped_column(String(32))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    actor = relationship("User", foreign_keys=[actor_id])
    case = relationship("Case", foreign_keys=[case_id])

class InvestigationFlag(Base):
    __tablename__ = "investigation_flags"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(String(128))
    resource_label: Mapped[str] = mapped_column(String(255))
    flagged_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    case = relationship("Case")
    flagged_by = relationship("User", foreign_keys=[flagged_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

