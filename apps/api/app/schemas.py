from datetime import datetime
from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel): investigator_id: str; password: str
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; investigator_id: str; name: str; role: str
class TokenResponse(BaseModel): access_token: str; token_type: str = "bearer"; user: UserOut
class AssignmentOut(BaseModel): assignment_role: str; user: UserOut
class CaseListOut(BaseModel):
    id: str; case_number: str; title: str; status: str; priority: str; updated_at: datetime
class CaseOut(CaseListOut):
    summary: str; created_at: datetime; lead_investigator: UserOut; assignments: list[AssignmentOut]
class RelatedCaseOut(BaseModel): case_number: str; title: str; status: str; investigating_officer: str; access_level: str
class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; evidence_id: str; case_id: str; case_number: str | None = None; filename: str; document_type: str; mime_type: str; document_language: str | None; ingestion_method: str = "document"; pipeline_version: str = "prompt4.5"; structured_json: dict | None = None; uploaded_by: UserOut; uploaded_at: datetime; updated_at: datetime; ocr_status: str; extraction_status: str; processing_status: str; integrity_status: str; notes: str | None; processing_error: str | None
class ExtractionOut(BaseModel):
    evidence_id: str; processing_status: str; ocr_status: str; extraction_status: str; language: dict | None; text: str | None; pages: list | None; entities: list[dict]; categories: dict; warnings: list[str]; error: str | None; processed_at: datetime | None; ingestion_method: str = "document"; structured: dict | None = None; relations: list[dict] = []; events: list[dict] = []
class EntityMentionOut(BaseModel):
    id: str; entity_id: str | None; entity_type: str; text: str; normalized_value: str; confidence: float; resolution_status: str; resolution_confidence: float | None; evidence_id: str
class EntityOut(BaseModel):
    id: str; entity_type: str; canonical_name: str; mentions: list[EntityMentionOut]; evidence_count: int
class ResolutionOut(BaseModel):
    id: str; source: EntityMentionOut; target: EntityMentionOut; confidence: float; reasons: list[str]; status: str
class RelationOut(BaseModel):
    id: str; relation_type: str; source: EntityMentionOut; target: EntityMentionOut; confidence: float; evidence_id: str; source_text: str; source_row: int | None = None; source_fields: list | None = None; observed_at: str | None
class EventOut(BaseModel):
    id: str; event_type: str; evidence_id: str; event_date: str | None; event_time: str | None; location: str | None; participants: list[EntityMentionOut]; confidence: float; source_text: str; source_row: int | None = None; source_fields: list | None = None
class GraphOut(BaseModel):
    nodes: list[dict]; edges: list[dict]
class TimelineOut(BaseModel):
    events: list[dict]
class IntelligenceOut(BaseModel):
    findings: list[dict]; degree: list[dict]; graphSize: dict
class IntegrityOut(BaseModel):
    evidence_id: str; sha256: str | None; current_hash: str | None = None; ledger_record_id: str | None; status: str; verified: bool; file_size: int | None; registered_at: datetime | None; verified_at: datetime | None
class CopilotRequest(BaseModel):
    question: str
class CopilotOut(BaseModel):
    answer: str; sources: list[str]
class AccessRequestCreate(BaseModel): case_number: str; resource_id: str | None = None; reason: str
class AccessDecision(BaseModel): decision: str
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; timestamp: datetime; actor_id: str | None; actor: UserOut | None = None; action: str; resource_type: str; resource_id: str | None; case_id: str | None; case_number: str | None = None; result: str; metadata_json: dict
class AccessRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; requester_id: str; case_id: str; resource_id: str | None; status: str; reason: str | None; created_at: datetime; reviewed_at: datetime | None; reviewed_by_id: str | None

class FlagCreate(BaseModel):
    resource_type: str  # EVIDENCE, ENTITY, EVENT, INTELLIGENCE
    resource_id: str
    resource_label: str
    reason: str

class FlagResolve(BaseModel):
    resolution_notes: str | None = None
    status: str = "RESOLVED"

class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    case_number: str | None = None
    resource_type: str
    resource_id: str
    resource_label: str
    flagged_by: UserOut
    reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: UserOut | None = None
    resolution_notes: str | None = None

