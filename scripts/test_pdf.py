import os
import sys
sys.path.insert(0, os.path.abspath("apps/api"))

from app.models import Case, User, Evidence, Entity, InvestigationFlag, AuditEvent
from app.database import SessionLocal
from app.graph import build_case_graph, timeline_for_case, intelligence_for_case
from app.report_generator import build_investigation_pdf
from sqlalchemy import select
from sqlalchemy.orm import selectinload

db = SessionLocal()
c = db.scalar(select(Case).where(Case.case_number == 'CASE-002'))

lead_name = c.lead_investigator.name if c.lead_investigator else "Unassigned"
lead_id = c.lead_investigator.investigator_id if c.lead_investigator else "-"
assigned_names = ", ".join([a.user.name for a in c.assignments if a.user]) or "None"
case_data = {
    "case_number": c.case_number,
    "title": c.title,
    "status": c.status,
    "priority": c.priority,
    "lead_investigator": f"{lead_name} ({lead_id})",
    "assigned": assigned_names,
    "summary": c.summary,
    "created_at": c.created_at,
}

evidences = db.scalars(select(Evidence).options(selectinload(Evidence.integrity)).where(Evidence.case_id == c.id)).all()
evidence_list = [
    {
        "evidence_id": ev.evidence_id,
        "filename": ev.filename,
        "document_type": ev.document_type,
        "method": ev.ingestion_method or "OCR",
        "sha256": ev.integrity.sha256 if ev.integrity else None,
        "integrity_status": ev.integrity.verification_status if ev.integrity else "NOT_REGISTERED",
    }
    for ev in evidences
]

entities_db = db.scalars(select(Entity).options(selectinload(Entity.mentions)).where(Entity.case_id == c.id)).all()
entities_list = [
    {
        "canonical_name": ent.canonical_name,
        "entity_type": ent.entity_type,
        "mention_count": len(ent.mentions),
        "evidence_count": len(set([m.evidence_id for m in ent.mentions if m.evidence_id])),
    }
    for ent in entities_db
]

graph = build_case_graph(db, c)
relations_list = [
    {
        "source": edge.get("source"),
        "target": edge.get("target"),
        "type": edge.get("type", "RELATED_TO"),
        "confidence": edge.get("confidence", 0.95),
    }
    for edge in graph.get("edges", [])
]

timeline = timeline_for_case(db, c)
timeline_events = [
    {
        "timestamp": item.get("timestamp") or item.get("date"),
        "type": item.get("type"),
        "description": item.get("description") or item.get("location"),
        "location": item.get("location"),
        "participants": ", ".join(item.get("participants", [])) if isinstance(item.get("participants"), list) else item.get("participants"),
    }
    for item in timeline
]

intel = intelligence_for_case(db, c)
intel_findings = intel.get("findings", [])

flags_db = db.scalars(select(InvestigationFlag).options(selectinload(InvestigationFlag.flagged_by)).where(InvestigationFlag.case_id == c.id)).all()
flagged_items = [
    {
        "resource_type": f.resource_type,
        "resource_label": f.resource_label,
        "flagged_by": f.flagged_by.name if f.flagged_by else "Investigator",
        "reason": f.reason,
        "status": f.status,
        "created_at": f.created_at,
    }
    for f in flags_db
]

audits_db = db.scalars(select(AuditEvent).options(selectinload(AuditEvent.actor)).where(AuditEvent.case_id == c.id).limit(10)).all()
audit_summary = [
    {
        "timestamp": au.timestamp,
        "actor": au.actor.name if au.actor else (au.actor_id or "System"),
        "action": au.action,
        "resource": f"{au.resource_type} ({au.resource_id or '-'})",
        "result": au.result,
    }
    for au in audits_db
]

pdf_bytes = build_investigation_pdf(
    case_data=case_data,
    evidence_list=evidence_list,
    entities_list=entities_list,
    relations_list=relations_list,
    timeline_events=timeline_events,
    intel_findings=intel_findings,
    flagged_items=flagged_items,
    audit_summary=audit_summary,
)

print("Direct PDF generation successful! Output size:", len(pdf_bytes), "bytes")
with open("CASE-002-Investigation-Report.pdf", "wb") as f:
    f.write(pdf_bytes)
print("Saved to CASE-002-Investigation-Report.pdf")
