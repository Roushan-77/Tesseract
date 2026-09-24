from pathlib import Path
import logging
from uuid import uuid4
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .access import has_case_access, is_case_lead
from .audit import record
from .config import settings
from .database import get_db
from .models import AccessRequest, AuditEvent, Case, CaseAssignment, Entity, EntityMentionRecord, EntityResolution, Event, EventParticipant, Evidence, EvidenceIntegrity, InvestigationFlag, Relation, User, now
from .schemas import AccessDecision, AccessRequestCreate, AccessRequestOut, AssignmentOut, AuditOut, CaseListOut, CaseOut, CopilotOut, CopilotRequest, EntityMentionOut, EntityOut, EventOut, EvidenceOut, ExtractionOut, FlagCreate, FlagOut, FlagResolve, GraphOut, IntelligenceOut, IntegrityOut, LoginRequest, RelatedCaseOut, RelationOut, ResolutionOut, TimelineOut, TokenResponse, UserOut
from .security import current_user, token_for, verify_password
from .processing import ProcessingError, process_document
from .intelligence import reconcile_prompt4
from .graph import build_case_graph, intelligence_for_case, timeline_for_case
from .neo4j_projection import rebuild_projection
from .storage import resolve_storage_key, save_upload
from .integrity import register, sha256_file
from .report_generator import build_investigation_pdf

app=FastAPI(title="Tesseract API",version="0.2.0")
logger = logging.getLogger(__name__)

cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins != "*" else ["*"]
if "*" in cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
def get_case(db,n):
    x=db.scalar(select(Case).options(selectinload(Case.assignments).selectinload(CaseAssignment.user),selectinload(Case.lead_investigator)).where(Case.case_number==n))
    if not x: raise HTTPException(404,"Case not found")
    return x
def permit(db,u,c):
    if not has_case_access(db,u,c): raise HTTPException(403,"Restricted access")
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/auth/login",response_model=TokenResponse)
def login(p:LoginRequest,db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.investigator_id==p.investigator_id))
    if not u or not verify_password(p.password, u.password_hash):
        record(db,actor_id=u.id if u else None,action="LOGIN_FAILURE",resource_type="AUTH",result="FAILURE")
        db.commit()
        raise HTTPException(401,"Invalid investigator ID or password")
    record(db,actor_id=u.id,action="LOGIN_SUCCESS",resource_type="AUTH",resource_id=u.id)
    db.commit()
    return TokenResponse(access_token=token_for(u),user=u)
@app.get("/me",response_model=UserOut)
def me(u:User=Depends(current_user)): return u
@app.get("/cases",response_model=list[CaseListOut])
def cases(status:str|None=None,priority:str|None=None,search:str|None=Query(None),db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=select(Case).join(CaseAssignment).where(CaseAssignment.user_id==u.id)
    if status:q=q.where(Case.status==status)
    if priority:q=q.where(Case.priority==priority)
    if search:q=q.where(Case.case_number.ilike(f"%{search}%")|Case.title.ilike(f"%{search}%"))
    return db.scalars(q.order_by(Case.updated_at.desc())).all()
@app.get("/cases/{n}",response_model=CaseOut)
def detail(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);record(db,actor_id=u.id,action="CASE_VIEWED",resource_type="CASE",resource_id=c.id,case_id=c.id);db.commit();return c
@app.get("/cases/{n}/assignments",response_model=list[AssignmentOut])
def assignments(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);return c.assignments
@app.get("/cases/{n}/related",response_model=list[RelatedCaseOut])
def related(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);targets=db.scalars(select(Case).where(Case.id!=c.id)).all()
    return [RelatedCaseOut(case_number=x.case_number,title=x.title,status=x.status,investigating_officer=x.lead_investigator.name,access_level="FULL" if has_case_access(db,u,x) else "RESTRICTED") for x in targets]
@app.get("/cases/{n}/evidence",response_model=list[EvidenceOut])
def list_evidence(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);return db.scalars(select(Evidence).options(selectinload(Evidence.uploaded_by)).where(Evidence.case_id==c.id).order_by(Evidence.uploaded_at.desc())).all()
def process_evidence_pipeline(db: Session, e: Evidence, actor_id: str) -> None:
    e.processing_status = "PROCESSING"
    e.ocr_status = "PROCESSING"
    e.extraction_status = "PROCESSING"
    e.processing_error = None
    record(db, actor_id=actor_id, action="EVIDENCE_PROCESSING_STARTED", resource_type="EVIDENCE", resource_id=e.evidence_id, case_id=e.case_id, result="PROCESSING")
    db.flush()
    try:
        path = resolve_storage_key(e.storage_key)
        result = process_document(path, e.mime_type)
        e.ocr_text = result["text"]
        e.ocr_pages = result["pages"]
        e.document_language = result["language"]["code"]
        e.language_confidence = result["language"]["confidence"]
        e.extraction_json = result
        e.ingestion_method = result.get("ingestion_method", "document")
        e.structured_json = result.get("structured")
        reconcile_prompt4(db, e, result)
        e.ocr_status = "COMPLETED"
        e.extraction_status = "COMPLETED"
        e.processing_status = "EXTRACTION_COMPLETED"
        e.processed_at = now()
        e.processing_error = None
        record(db, actor_id=actor_id, action="RELATIONSHIP_EXTRACTION_COMPLETED", resource_type="EVIDENCE", resource_id=e.evidence_id, case_id=e.case_id, result="SUCCESS")
        record(db, actor_id=actor_id, action="EVIDENCE_OCR_COMPLETED", resource_type="EVIDENCE", resource_id=e.evidence_id, case_id=e.case_id, result="SUCCESS")
        record(db, actor_id=actor_id, action="EVIDENCE_EXTRACTION_COMPLETED", resource_type="EVIDENCE", resource_id=e.evidence_id, case_id=e.case_id, result="SUCCESS")
    except ProcessingError as exc:
        message = str(exc)
        e.ocr_status = "FAILED"
        e.extraction_status = "FAILED"
        e.processing_status = "FAILED"
        e.processing_error = message
        record(db, actor_id=actor_id, action="EVIDENCE_PROCESSING_FAILED", resource_type="EVIDENCE", resource_id=e.evidence_id, case_id=e.case_id, result="FAILED", metadata={"error": message})
    except Exception as exc:
        logger.exception("Evidence processing failed for %s", e.evidence_id)
        message = f"Evidence processing failed: {str(exc)}" if str(exc) else "Evidence processing failed. Check file format."
        e.ocr_status = "FAILED"
        e.extraction_status = "FAILED"
        e.processing_status = "FAILED"
        e.processing_error = message
        record(db, actor_id=actor_id, action="EVIDENCE_PROCESSING_FAILED", resource_type="EVIDENCE", resource_id=e.evidence_id, case_id=e.case_id, result="FAILED")


def extraction_response(e: Evidence, db: Session | None = None) -> ExtractionOut:
    result = e.extraction_json or {}
    language = result.get("language") if result else None
    structured = e.structured_json or result.get("structured")

    # 1. Structured fallback from CSV text if needed
    if not structured and (e.filename.endswith(".csv") or e.ingestion_method == "structured") and e.ocr_text:
        try:
            import csv
            import io
            reader = csv.DictReader(io.StringIO(e.ocr_text.strip()))
            fieldnames = reader.fieldnames or []
            rows = []
            for idx, row in enumerate(reader, start=1):
                rows.append({"row": idx, "fields": {k: str(v or "") for k, v in row.items()}})
            if fieldnames:
                structured = {
                    "records": rows,
                    "row_count": len(rows),
                    "column_count": len(fieldnames),
                    "columns": fieldnames,
                    "file_type": "CSV",
                }
        except Exception:
            pass

    # 2. Entity mentions fallback
    entities = result.get("entities", [])
    if not entities and db:
        db_mentions = db.scalars(select(EntityMentionRecord).where(EntityMentionRecord.evidence_id == e.id)).all()
        if db_mentions:
            entities = [
                {
                    "mentionId": m.id,
                    "type": m.entity_type,
                    "text": m.text,
                    "normalizedValue": m.normalized_value,
                    "start": m.start or 0,
                    "end": m.end or 0,
                    "confidence": m.confidence or 0.95,
                }
                for m in db_mentions
            ]
    elif not entities and hasattr(e, "mentions") and e.mentions:
        entities = [
            {
                "mentionId": m.id,
                "type": m.entity_type,
                "text": m.text,
                "normalizedValue": m.normalized_value,
                "start": m.start or 0,
                "end": m.end or 0,
                "confidence": m.confidence or 0.95,
            }
            for m in e.mentions
        ]

    # 3. Categories grouping
    categories = result.get("categories", {})
    if not categories and entities:
        categories = {}
        for ent in entities:
            t = ent["type"]
            categories.setdefault(t, []).append(ent)

    # 4. Relations fallback
    relations = result.get("relations", [])
    if not relations and db:
        db_rels = db.scalars(select(Relation).where(Relation.evidence_id == e.id)).all()
        for r in db_rels:
            s_mention = db.get(EntityMentionRecord, r.source_mention_id)
            t_mention = db.get(EntityMentionRecord, r.target_mention_id)
            relations.append({
                "type": r.relation_type,
                "source": {
                    "mentionId": s_mention.id if s_mention else r.source_mention_id,
                    "type": s_mention.entity_type if s_mention else "ENTITY",
                    "text": s_mention.text if s_mention else r.source_text,
                    "normalizedValue": s_mention.normalized_value if s_mention else r.source_text,
                    "confidence": r.confidence,
                    "start": 0, "end": 0,
                },
                "target": {
                    "mentionId": t_mention.id if t_mention else r.target_mention_id,
                    "type": t_mention.entity_type if t_mention else "ENTITY",
                    "text": t_mention.text if t_mention else "",
                    "normalizedValue": t_mention.normalized_value if t_mention else "",
                    "confidence": r.confidence,
                    "start": 0, "end": 0,
                },
                "sourceText": r.source_text,
                "confidence": r.confidence,
                "sourceRow": r.source_row,
            })

    # 5. Events fallback
    events = result.get("events", [])
    if not events and db:
        db_evs = db.scalars(select(Event).where(Event.evidence_id == e.id)).all()
        for ev in db_evs:
            parts = db.scalars(select(EventParticipant).where(EventParticipant.event_id == ev.id)).all()
            part_mentions = []
            for p in parts:
                pm = db.get(EntityMentionRecord, p.mention_id)
                if pm:
                    part_mentions.append({
                        "mentionId": pm.id,
                        "type": pm.entity_type,
                        "text": pm.text,
                        "normalizedValue": pm.normalized_value,
                        "confidence": ev.confidence,
                        "start": 0, "end": 0,
                    })
            events.append({
                "type": ev.event_type,
                "date": f"{ev.event_date or ''} {ev.event_time or ''}".strip() or None,
                "location": {
                    "text": ev.source_text,
                    "type": "LOCATION",
                    "mentionId": ev.id,
                    "normalizedValue": ev.source_text,
                    "confidence": ev.confidence,
                    "start": 0, "end": 0,
                } if ev.location_entity_id else None,
                "participants": part_mentions,
                "sourceText": ev.source_text,
                "confidence": ev.confidence,
                "sourceRow": ev.source_row,
            })

    return ExtractionOut(
        evidence_id=e.evidence_id,
        processing_status=e.processing_status,
        ocr_status=e.ocr_status,
        extraction_status=e.extraction_status,
        language=language or ({"code": e.document_language or "en", "confidence": 0.99} if e.document_language else {"code": "en", "confidence": 0.99}),
        text=e.ocr_text,
        pages=e.ocr_pages,
        entities=entities,
        categories=categories,
        warnings=result.get("warnings", []),
        error=e.processing_error,
        processed_at=e.processed_at,
        ingestion_method=e.ingestion_method or ("structured" if e.filename.endswith(".csv") else "document"),
        structured=structured,
        relations=relations,
        events=events,
    )


@app.post("/cases/{n}/evidence", response_model=EvidenceOut)
def upload(
    n: str,
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    document_language: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    u: User = Depends(current_user)
):
    c = get_case(db, n)
    permit(db, u, c)
    incoming_files = []
    if files:
        incoming_files.extend(files)
    if file and file not in incoming_files:
        incoming_files.append(file)
    if not incoming_files:
        raise HTTPException(400, "No file provided for upload.")

    created_evidence = []
    for upload_file in incoming_files:
        eid = f"EVD-{n.split('-')[-1]}-{uuid4().hex[:8].upper()}"
        try:
            key = save_upload(eid, upload_file)
        except ValueError as e:
            raise HTTPException(400, str(e))
        
        filename = Path(upload_file.filename or "evidence").name
        ext = Path(filename).suffix.lstrip('.').upper() or "FILE"
        e = Evidence(
            evidence_id=eid,
            case_id=c.id,
            filename=filename,
            document_type=ext,
            mime_type=upload_file.content_type or "application/octet-stream",
            storage_key=key,
            uploaded_by_id=u.id,
            document_language=document_language,
            notes=notes,
            ocr_status="PROCESSING",
            extraction_status="PROCESSING",
            processing_status="PROCESSING",
            integrity_status="NOT_REGISTERED"
        )
        db.add(e)
        db.flush()
        
        storage_path = resolve_storage_key(key)
        integrity = register(storage_path, eid, u.id)
        integrity.evidence_id = e.id
        integrity.verification_status = "VERIFIED"
        integrity.verified_at = now()
        db.add(integrity)
        e.integrity_status = "VERIFIED"
        record(db, actor_id=u.id, action="EVIDENCE_UPLOADED", resource_type="EVIDENCE", resource_id=eid, case_id=c.id, metadata={"filename": e.filename})
        record(db, actor_id=u.id, action="EVIDENCE_HASH_REGISTERED", resource_type="EVIDENCE", resource_id=eid, case_id=c.id, metadata={"sha256": integrity.sha256, "ledger_record_id": integrity.ledger_record_id})
        
        process_evidence_pipeline(db, e, u.id)
        created_evidence.append(e)

    db.commit()
    for item in created_evidence:
        db.refresh(item)
    return created_evidence[0]


@app.post("/cases/{n}/evidence/batch", response_model=list[EvidenceOut])
def batch_upload(
    n: str,
    files: list[UploadFile] = File(...),
    document_language: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    u: User = Depends(current_user)
):
    c = get_case(db, n)
    permit(db, u, c)
    if not files:
        raise HTTPException(400, "No files provided for batch upload.")

    created_evidence = []
    for upload_file in files:
        eid = f"EVD-{n.split('-')[-1]}-{uuid4().hex[:8].upper()}"
        try:
            key = save_upload(eid, upload_file)
        except ValueError as e:
            raise HTTPException(400, str(e))
        
        filename = Path(upload_file.filename or "evidence").name
        ext = Path(filename).suffix.lstrip('.').upper() or "FILE"
        e = Evidence(
            evidence_id=eid,
            case_id=c.id,
            filename=filename,
            document_type=ext,
            mime_type=upload_file.content_type or "application/octet-stream",
            storage_key=key,
            uploaded_by_id=u.id,
            document_language=document_language,
            notes=notes,
            ocr_status="PROCESSING",
            extraction_status="PROCESSING",
            processing_status="PROCESSING",
            integrity_status="NOT_REGISTERED"
        )
        db.add(e)
        db.flush()
        
        storage_path = resolve_storage_key(key)
        integrity = register(storage_path, eid, u.id)
        integrity.evidence_id = e.id
        integrity.verification_status = "VERIFIED"
        integrity.verified_at = now()
        db.add(integrity)
        e.integrity_status = "VERIFIED"
        record(db, actor_id=u.id, action="EVIDENCE_UPLOADED", resource_type="EVIDENCE", resource_id=eid, case_id=c.id, metadata={"filename": e.filename})
        record(db, actor_id=u.id, action="EVIDENCE_HASH_REGISTERED", resource_type="EVIDENCE", resource_id=eid, case_id=c.id, metadata={"sha256": integrity.sha256, "ledger_record_id": integrity.ledger_record_id})
        
        process_evidence_pipeline(db, e, u.id)
        created_evidence.append(e)

    db.commit()
    for item in created_evidence:
        db.refresh(item)
    return created_evidence


@app.post("/evidence/{eid}/process", response_model=ExtractionOut)
def process(eid: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    e = db.scalar(select(Evidence).options(selectinload(Evidence.case)).where(Evidence.evidence_id == eid))
    if not e: raise HTTPException(404, "Evidence not found")
    permit(db, u, e.case)
    process_evidence_pipeline(db, e, u.id)
    db.commit()
    db.refresh(e)
    return extraction_response(e, db=db)
@app.get("/evidence/{eid}",response_model=EvidenceOut)
def evidence(eid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    e=db.scalar(select(Evidence).options(selectinload(Evidence.uploaded_by),selectinload(Evidence.case)).where(Evidence.evidence_id==eid))
    if not e:raise HTTPException(404,"Evidence not found")
    permit(db,u,e.case);record(db,actor_id=u.id,action="EVIDENCE_VIEWED",resource_type="EVIDENCE",resource_id=eid,case_id=e.case_id);db.commit();return {**EvidenceOut.model_validate(e, from_attributes=True).model_dump(), "case_number": e.case.case_number}
@app.get("/evidence/{eid}/extraction",response_model=ExtractionOut)
def extraction(eid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    e=db.scalar(select(Evidence).options(selectinload(Evidence.case)).where(Evidence.evidence_id==eid))
    if not e:raise HTTPException(404,"Evidence not found")
    permit(db,u,e.case);record(db,actor_id=u.id,action="EVIDENCE_EXTRACTION_VIEWED",resource_type="EVIDENCE",resource_id=eid,case_id=e.case_id);db.commit();return extraction_response(e, db=db)
@app.get("/evidence/{eid}/file")
def evidence_file(eid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    e=db.scalar(select(Evidence).options(selectinload(Evidence.case)).where(Evidence.evidence_id==eid))
    if not e:raise HTTPException(404,"Evidence not found")
    permit(db,u,e.case);record(db,actor_id=u.id,action="EVIDENCE_VIEWED",resource_type="EVIDENCE",resource_id=eid,case_id=e.case_id);db.commit()
    path=resolve_storage_key(e.storage_key)
    if not path.is_file():raise HTTPException(404,"Stored file not found")
    return FileResponse(path,media_type=e.mime_type,filename=e.filename)
@app.get("/evidence/{eid}/integrity",response_model=IntegrityOut)
def evidence_integrity(eid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    e=db.scalar(select(Evidence).options(selectinload(Evidence.case),selectinload(Evidence.integrity)).where(Evidence.evidence_id==eid))
    if not e: raise HTTPException(404,"Evidence not found")
    permit(db,u,e.case); record(db,actor_id=u.id,action="INTEGRITY_VIEWED",resource_type="EVIDENCE",resource_id=eid,case_id=e.case_id); db.commit()
    item=e.integrity
    status = item.verification_status if item else "NOT_REGISTERED"
    return IntegrityOut(evidence_id=eid,sha256=item.sha256 if item else None,ledger_record_id=item.ledger_record_id if item else None,status=status,verified=status=="VERIFIED",file_size=item.file_size if item else None,registered_at=item.registered_at if item else None,verified_at=item.verified_at if item else None)
@app.post("/evidence/{eid}/verify-integrity",response_model=IntegrityOut)
def verify_integrity(eid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    e=db.scalar(select(Evidence).options(selectinload(Evidence.case),selectinload(Evidence.integrity)).where(Evidence.evidence_id==eid))
    if not e: raise HTTPException(404,"Evidence not found")
    permit(db,u,e.case)
    if not e.integrity:
        path = resolve_storage_key(e.storage_key)
        if not path.is_file(): raise HTTPException(404, "Stored file not found for integrity registration")
        item = register(path, eid, u.id)
        item.evidence_id = e.id
        item.verification_status = "VERIFIED"
        item.verified_at = now()
        db.add(item)
        e.integrity = item
        e.integrity_status = "VERIFIED"
        record(db, actor_id=u.id, action="INTEGRITY_REGISTERED", resource_type="EVIDENCE", resource_id=eid, case_id=e.case_id, result="SUCCESS", metadata={"sha256": item.sha256, "ledger_record_id": item.ledger_record_id})
        db.commit()
        db.refresh(e)
    path = resolve_storage_key(e.storage_key)
    current_hash, size = sha256_file(path) if path.is_file() else (None, 0)
    verified = current_hash is not None and current_hash == e.integrity.sha256
    e.integrity.verification_status = "VERIFIED" if verified else "MODIFIED"
    e.integrity.verified_at = now()
    e.integrity_status = e.integrity.verification_status
    record(db, actor_id=u.id, action="INTEGRITY_VERIFIED" if verified else "INTEGRITY_FAILED", resource_type="EVIDENCE", resource_id=eid, case_id=e.case_id, result=e.integrity.verification_status, metadata={"registered_hash": e.integrity.sha256, "current_hash": current_hash})
    db.commit()
    return IntegrityOut(evidence_id=eid, sha256=e.integrity.sha256, current_hash=current_hash, ledger_record_id=e.integrity.ledger_record_id, status=e.integrity.verification_status, verified=verified, file_size=size, registered_at=e.integrity.registered_at, verified_at=e.integrity.verified_at)
def mention_out(m:EntityMentionRecord) -> EntityMentionOut:
    return EntityMentionOut(id=m.id,entity_id=m.entity_id,entity_type=m.entity_type,text=m.text,normalized_value=m.normalized_value,confidence=m.confidence,resolution_status=m.resolution_status,resolution_confidence=m.resolution_confidence,evidence_id=m.evidence_id)
@app.get("/cases/{n}/entities",response_model=list[EntityOut])
def case_entities(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);items=db.scalars(select(Entity).where(Entity.case_id==c.id).order_by(Entity.entity_type,Entity.canonical_name)).all();return [EntityOut(id=item.id,entity_type=item.entity_type,canonical_name=item.canonical_name,mentions=[mention_out(m) for m in db.scalars(select(EntityMentionRecord).where(EntityMentionRecord.entity_id==item.id)).all()],evidence_count=len({m.evidence_id for m in db.scalars(select(EntityMentionRecord).where(EntityMentionRecord.entity_id==item.id)).all()})) for item in items]
@app.get("/cases/{n}/relationships",response_model=list[RelationOut])
def case_relationships(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);items=db.scalars(select(Relation).where(Relation.case_id==c.id).order_by(Relation.created_at.desc())).all();return [RelationOut(id=item.id,relation_type=item.relation_type,source=mention_out(db.get(EntityMentionRecord,item.source_mention_id)),target=mention_out(db.get(EntityMentionRecord,item.target_mention_id)),confidence=item.confidence,evidence_id=db.get(Evidence,item.evidence_id).evidence_id,source_text=item.source_text,source_row=item.source_row,source_fields=item.source_fields,observed_at=item.observed_at) for item in items]
@app.get("/cases/{n}/events",response_model=list[EventOut])
def case_events(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);items=db.scalars(select(Event).where(Event.case_id==c.id).order_by(Event.created_at.desc())).all();events=[]
    for item in items:
        participant_ids=db.scalars(select(EventParticipant.mention_id).where(EventParticipant.event_id==item.id)).all();location=db.get(Entity,item.location_entity_id) if item.location_entity_id else None
        events.append(EventOut(id=item.id,event_type=item.event_type,evidence_id=db.get(Evidence,item.evidence_id).evidence_id,event_date=item.event_date,event_time=item.event_time,location=location.canonical_name if location else None,participants=[mention_out(db.get(EntityMentionRecord,mention_id)) for mention_id in participant_ids],confidence=item.confidence,source_text=item.source_text,source_row=item.source_row,source_fields=item.source_fields))
    return events
@app.get("/cases/{n}/graph",response_model=GraphOut)
def case_graph(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);record(db,actor_id=u.id,action="GRAPH_VIEWED",resource_type="CASE",resource_id=c.id,case_id=c.id);db.commit();return build_case_graph(db,c)
@app.get("/cases/{n}/timeline",response_model=TimelineOut)
def case_timeline(n:str,event_type:str|None=None,entity:str|None=None,location:str|None=None,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);record(db,actor_id=u.id,action="TIMELINE_VIEWED",resource_type="CASE",resource_id=c.id,case_id=c.id);db.commit();return {"events":timeline_for_case(db,c,event_type,entity,location)}
@app.get("/cases/{n}/intelligence",response_model=IntelligenceOut)
def case_intelligence(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);record(db,actor_id=u.id,action="INTELLIGENCE_VIEWED",resource_type="CASE",resource_id=c.id,case_id=c.id);db.commit();return intelligence_for_case(db,c)
@app.post("/cases/{n}/graph/rebuild")
def rebuild_case_graph(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n)
    if not is_case_lead(c,u): raise HTTPException(403,"Only the case lead can rebuild the graph projection")
    result=rebuild_projection(build_case_graph(db,c));record(db,actor_id=u.id,action="GRAPH_REBUILT",resource_type="CASE",resource_id=c.id,case_id=c.id,metadata=result);db.commit();return result
@app.get("/entity-resolutions",response_model=list[ResolutionOut])
def resolutions(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c);items=db.scalars(select(EntityResolution).join(EntityMentionRecord,EntityResolution.source_mention_id==EntityMentionRecord.id).join(Evidence,EntityMentionRecord.evidence_id==Evidence.id).where(Evidence.case_id==c.id,EntityResolution.status=="SUGGESTED")).all();return [ResolutionOut(id=item.id,source=mention_out(db.get(EntityMentionRecord,item.source_mention_id)),target=mention_out(db.get(EntityMentionRecord,item.target_mention_id)),confidence=item.confidence,reasons=item.reasons,status=item.status) for item in items]
def resolve_review(rid:str,decision:str,db:Session,u:User):
    item=db.get(EntityResolution,rid)
    if not item:raise HTTPException(404,"Resolution suggestion not found")
    source=db.get(EntityMentionRecord,item.source_mention_id);target=db.get(EntityMentionRecord,item.target_mention_id);source_evidence=db.get(Evidence,source.evidence_id);target_evidence=db.get(Evidence,target.evidence_id)
    if source_evidence.case_id!=target_evidence.case_id:raise HTTPException(403,"Resolution crosses cases")
    case=db.get(Case,source_evidence.case_id);permit(db,u,case)
    item.status=decision;item.reviewed_at=now()
    if decision=="CONFIRMED": target.entity_id=source.entity_id;source.resolution_status="CONFIRMED";target.resolution_status="CONFIRMED";source.resolution_confidence=item.confidence;target.resolution_confidence=item.confidence
    else: source.resolution_status="REJECTED";target.resolution_status="REJECTED"
    record(db,actor_id=u.id,action=f"ENTITY_RESOLUTION_{decision}",resource_type="ENTITY_RESOLUTION",resource_id=rid,case_id=case.id,result=decision);db.commit();return {"status":decision}
@app.post("/entity-resolutions/{rid}/confirm")
def confirm_resolution(rid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):return resolve_review(rid,"CONFIRMED",db,u)
@app.post("/entity-resolutions/{rid}/reject")
def reject_resolution(rid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):return resolve_review(rid,"REJECTED",db,u)
@app.post("/access-requests",response_model=AccessRequestOut)
def create_request(p:AccessRequestCreate,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,p.case_number)
    if has_case_access(db,u,c):raise HTTPException(400,"You already have access to this case")
    old=db.scalar(select(AccessRequest).where(AccessRequest.requester_id==u.id,AccessRequest.case_id==c.id,AccessRequest.resource_id==p.resource_id,AccessRequest.status=="PENDING"))
    if old:return old
    r=AccessRequest(requester_id=u.id,case_id=c.id,resource_id=p.resource_id,reason=p.reason,status="PENDING");db.add(r);record(db,actor_id=u.id,action="ACCESS_REQUEST_CREATED",resource_type="CASE",resource_id=c.case_number,case_id=c.id,result="PENDING");db.commit();db.refresh(r);return r
@app.get("/access-requests",response_model=list[AccessRequestOut])
def requests(scope:str="outgoing",db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=select(AccessRequest).order_by(AccessRequest.created_at.desc())
    return db.scalars(q.join(Case).where(Case.lead_investigator_id==u.id) if scope=="incoming" else q.where(AccessRequest.requester_id==u.id)).all()
@app.patch("/access-requests/{rid}",response_model=AccessRequestOut)
def decide(rid:str,p:AccessDecision,db:Session=Depends(get_db),u:User=Depends(current_user)):
    r=db.get(AccessRequest,rid);c=db.get(Case,r.case_id) if r else None
    if not r:raise HTTPException(404,"Request not found")
    if not is_case_lead(c,u):raise HTTPException(403,"Only the case lead can decide")
    if r.status!="PENDING" or p.decision not in {"GRANTED","DENIED"}:raise HTTPException(400,"Invalid request decision")
    r.status=p.decision;r.reviewed_by_id=u.id;r.reviewed_at=now();record(db,actor_id=u.id,action=f"ACCESS_REQUEST_{p.decision}",resource_type="ACCESS_REQUEST",resource_id=r.id,case_id=c.id,result=p.decision);db.commit();db.refresh(r);return r
@app.get("/audit-events",response_model=list[AuditOut])
def audit(case_number:str|None=None,evidence_id:str|None=None,db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=select(AuditEvent).options(selectinload(AuditEvent.actor),selectinload(AuditEvent.case))
    if case_number:
        c=get_case(db,case_number); permit(db,u,c); q=q.where(AuditEvent.case_id==c.id)
    else:
        q=q.where(AuditEvent.actor_id==u.id)
    if evidence_id: q=q.where(AuditEvent.resource_id==evidence_id)
    items=db.scalars(q.order_by(AuditEvent.timestamp.desc()).limit(200)).all()
    res=[]
    for item in items:
        out=AuditOut.model_validate(item,from_attributes=True)
        if item.case: out.case_number=item.case.case_number
        res.append(out)
    return res
@app.post("/cases/{n}/copilot",response_model=CopilotOut)
def copilot(n:str,request:CopilotRequest,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c); graph=build_case_graph(db,c); intel=intelligence_for_case(db,c); events=timeline_for_case(db,c)
    question=request.question.casefold(); sources=[]
    if "chronolog" in question or "event" in question:
        answer=f"The accessible case contains {len(events)} recorded events."
        sources=[event["evidenceId"] for event in events if event.get("evidenceId")]
    elif "anomal" in question or "spike" in question or "unusual" in question or "suspicious" in question:
        anomalies = [f for f in intel["findings"] if f.get("type") in {"ANOMALY", "TEMPORAL_ANOMALY"} or "Spike" in f.get("title", "") or "Unusual" in f.get("title", "")]
        if anomalies:
            answer = " ".join(f"[{a['title']}]: {a['explanation']}" for a in anomalies)
            sources = [eid for a in anomalies for eid in a.get("evidenceIds", [])]
        else:
            answer = "No behavioral or transactional anomalies detected in this case."
            sources = []
    elif "connect" in question or "central" in question:
        finding=next((f for f in intel["findings"] if f.get("title") == "Highly connected entity"), intel["findings"][0] if intel["findings"] else None)
        answer=f"{finding['explanation']} This is a graph-structural finding and does not by itself establish criminal involvement." if finding else "I don't have sufficient accessible evidence to identify a structurally central entity."
        sources=finding["evidenceIds"] if finding else []
    elif "summar" in question or "case" in question:
        answer=f"{c.case_number}: {c.title}. The accessible record contains {len(graph['nodes'])} graph nodes, {len(graph['edges'])} observed links, and {len(events)} events."
        sources=[item["evidenceId"] for item in events if item.get("evidenceId")]
    else: answer="I don't have sufficient accessible evidence to answer that."
    record(db,actor_id=u.id,action="COPILOT_QUERY",resource_type="CASE",resource_id=c.id,case_id=c.id,result="SUCCESS");db.commit();return CopilotOut(answer=answer,sources=sorted(set(sources)))
@app.get("/cases/{n}/flags", response_model=list[FlagOut])
def get_case_flags(n: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    c = get_case(db, n)
    permit(db, u, c)
    flags = db.scalars(
        select(InvestigationFlag)
        .options(selectinload(InvestigationFlag.flagged_by), selectinload(InvestigationFlag.resolved_by))
        .where(InvestigationFlag.case_id == c.id)
        .order_by(InvestigationFlag.created_at.desc())
    ).all()
    return [
        FlagOut(
            id=f.id,
            case_id=f.case_id,
            case_number=c.case_number,
            resource_type=f.resource_type,
            resource_id=f.resource_id,
            resource_label=f.resource_label,
            flagged_by=UserOut.model_validate(f.flagged_by, from_attributes=True),
            reason=f.reason,
            status=f.status,
            created_at=f.created_at,
            resolved_at=f.resolved_at,
            resolved_by=UserOut.model_validate(f.resolved_by, from_attributes=True) if f.resolved_by else None,
            resolution_notes=f.resolution_notes,
        )
        for f in flags
    ]

@app.post("/cases/{n}/flags", response_model=FlagOut)
def create_case_flag(n: str, p: FlagCreate, db: Session = Depends(get_db), u: User = Depends(current_user)):
    c = get_case(db, n)
    permit(db, u, c)
    flag = InvestigationFlag(
        case_id=c.id,
        resource_type=p.resource_type,
        resource_id=p.resource_id,
        resource_label=p.resource_label,
        flagged_by_id=u.id,
        reason=p.reason,
        status="ACTIVE",
    )
    db.add(flag)
    db.flush()
    record(
        db,
        actor_id=u.id,
        action="FLAG_CREATED",
        resource_type=f"FLAG_{p.resource_type.upper()}",
        resource_id=flag.id,
        case_id=c.id,
        result="SUCCESS",
        metadata={"resource_id": p.resource_id, "resource_label": p.resource_label, "reason": p.reason}
    )
    db.commit()
    db.refresh(flag)
    return FlagOut(
        id=flag.id,
        case_id=flag.case_id,
        case_number=c.case_number,
        resource_type=flag.resource_type,
        resource_id=flag.resource_id,
        resource_label=flag.resource_label,
        flagged_by=UserOut.model_validate(u, from_attributes=True),
        reason=flag.reason,
        status=flag.status,
        created_at=flag.created_at,
    )

@app.post("/cases/{n}/flags/{fid}/resolve", response_model=FlagOut)
def resolve_case_flag(n: str, fid: str, p: FlagResolve, db: Session = Depends(get_db), u: User = Depends(current_user)):
    c = get_case(db, n)
    permit(db, u, c)
    flag = db.scalar(
        select(InvestigationFlag)
        .options(selectinload(InvestigationFlag.flagged_by))
        .where(InvestigationFlag.id == fid, InvestigationFlag.case_id == c.id)
    )
    if not flag:
        raise HTTPException(404, "Investigation flag not found")
    flag.status = p.status or "RESOLVED"
    flag.resolved_at = now()
    flag.resolved_by_id = u.id
    flag.resolution_notes = p.resolution_notes
    record(
        db,
        actor_id=u.id,
        action=f"FLAG_{flag.status.upper()}",
        resource_type=f"FLAG_{flag.resource_type.upper()}",
        resource_id=flag.id,
        case_id=c.id,
        result="SUCCESS",
        metadata={"resolution_notes": p.resolution_notes, "status": flag.status}
    )
    db.commit()
    db.refresh(flag)
    return FlagOut(
        id=flag.id,
        case_id=flag.case_id,
        case_number=c.case_number,
        resource_type=flag.resource_type,
        resource_id=flag.resource_id,
        resource_label=flag.resource_label,
        flagged_by=UserOut.model_validate(flag.flagged_by, from_attributes=True),
        reason=flag.reason,
        status=flag.status,
        created_at=flag.created_at,
        resolved_at=flag.resolved_at,
        resolved_by=UserOut.model_validate(u, from_attributes=True),
        resolution_notes=flag.resolution_notes,
    )

@app.delete("/cases/{n}/flags/{fid}")
def delete_case_flag(n: str, fid: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    c = get_case(db, n)
    permit(db, u, c)
    flag = db.get(InvestigationFlag, fid)
    if not flag or flag.case_id != c.id:
        raise HTTPException(404, "Investigation flag not found")
    record(
        db,
        actor_id=u.id,
        action="FLAG_REMOVED",
        resource_type=f"FLAG_{flag.resource_type.upper()}",
        resource_id=flag.id,
        case_id=c.id,
        result="SUCCESS",
        metadata={"resource_id": flag.resource_id, "resource_label": flag.resource_label}
    )
    db.delete(flag)
    db.commit()
    return {"status": "REMOVED"}

@app.get("/cases/{n}/report")
def report(n:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=get_case(db,n);permit(db,u,c); graph=build_case_graph(db,c); timeline=timeline_for_case(db,c); intel=intelligence_for_case(db,c); integrity=db.scalars(select(EvidenceIntegrity).join(Evidence).where(Evidence.case_id==c.id)).all()
    lines=[f"TESSERACT INVESTIGATION REPORT - {c.case_number}",c.title,"",f"Generated: {now().isoformat()}","","EXECUTIVE SUMMARY",c.summary,"",f"Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges",f"Timeline events: {len(timeline)}","","STRUCTURAL FINDINGS"]+[f"- {finding['explanation']} Evidence: {', '.join(finding['evidenceIds']) or '-'}" for finding in intel["findings"]]+["","EVIDENCE INTEGRITY",f"Registered records: {len(integrity)}"]
    record(db,actor_id=u.id,action="REPORT_GENERATED",resource_type="CASE",resource_id=c.id,case_id=c.id,result="SUCCESS");db.commit();return {"case_number":c.case_number,"content":"\n".join(lines),"sources":sorted({item for finding in intel["findings"] for item in finding["evidenceIds"]})}

@app.get("/cases/{n}/report.pdf")
def report_pdf(n: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    c = get_case(db, n)
    permit(db, u, c)
    lead_name = c.lead_investigator.name if c.lead_investigator else "Unassigned"
    assigned_names = ", ".join([a.user.name for a in c.assignments if a.user]) or "None"
    case_data = {
        "case_number": c.case_number,
        "title": c.title,
        "status": c.status,
        "priority": c.priority,
        "lead_investigator": f"{lead_name} ({c.lead_investigator.investigator_id if c.lead_investigator else '-'})",
        "assigned": assigned_names,
        "summary": c.summary,
        "created_at": c.created_at,
    }
    evidences = db.scalars(
        select(Evidence)
        .options(selectinload(Evidence.integrity))
        .where(Evidence.case_id == c.id)
    ).all()
    evidence_list = [
        {
            "evidence_id": ev.evidence_id,
            "filename": ev.filename,
            "document_type": ev.document_type,
            "method": ev.ingestion_method or ("Structured Parsing" if ev.filename.endswith(".csv") else "OCR"),
            "sha256": ev.integrity.sha256 if ev.integrity else None,
            "integrity_status": ev.integrity.verification_status if ev.integrity else "NOT_REGISTERED",
        }
        for ev in evidences
    ]
    entities_db = db.scalars(
        select(Entity)
        .options(selectinload(Entity.mentions))
        .where(Entity.case_id == c.id)
    ).all()
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
    flags_db = db.scalars(
        select(InvestigationFlag)
        .options(selectinload(InvestigationFlag.flagged_by))
        .where(InvestigationFlag.case_id == c.id)
        .order_by(InvestigationFlag.created_at.desc())
    ).all()
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
    audits_db = db.scalars(
        select(AuditEvent)
        .options(selectinload(AuditEvent.actor))
        .where(AuditEvent.case_id == c.id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(10)
    ).all()
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
    record(db, actor_id=u.id, action="REPORT_DOWNLOADED", resource_type="CASE", resource_id=c.id, case_id=c.id, result="SUCCESS")
    db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{c.case_number}-Investigation-Report.pdf"'}
    )
