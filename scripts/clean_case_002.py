import os
import shutil
import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.database import SessionLocal
from app.models import (
    Case,
    Evidence,
    EvidenceIntegrity,
    Entity,
    EntityMentionRecord,
    EntityResolution,
    Relation,
    Event,
    EventParticipant,
    AuditEvent,
    AccessRequest
)
from app.storage import STORAGE_ROOT

def clean_case_002():
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_number == "CASE-002").first()
        if not case:
            print("CASE-002 not found in database.")
            return

        print(f"Found Case: {case.case_number} (ID: {case.id})")

        # 1. Get all evidence for CASE-002
        evidence_list = db.query(Evidence).filter(Evidence.case_id == case.id).all()
        evidence_ids = [e.id for e in evidence_list]
        print(f"Found {len(evidence_list)} evidence records for CASE-002.")

        # Remove physical files
        for ev in evidence_list:
            if ev.evidence_id:
                folder = STORAGE_ROOT / ev.evidence_id
                if folder.exists():
                    shutil.rmtree(folder, ignore_errors=True)
                    print(f"Deleted storage folder: {folder}")
            if ev.storage_key:
                try:
                    file_path = STORAGE_ROOT / ev.storage_key
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass

        # 2. Mentions
        mentions = db.query(EntityMentionRecord).filter(EntityMentionRecord.evidence_id.in_(evidence_ids)).all() if evidence_ids else []
        mention_ids = [m.id for m in mentions]
        print(f"Found {len(mentions)} entity mentions for CASE-002.")

        # 3. Resolutions
        if mention_ids:
            resolutions = db.query(EntityResolution).filter(
                (EntityResolution.source_mention_id.in_(mention_ids)) | 
                (EntityResolution.target_mention_id.in_(mention_ids))
            ).all()
            print(f"Deleting {len(resolutions)} entity resolutions for CASE-002...")
            for res in resolutions:
                db.delete(res)
            db.flush()

        # 4. Relations
        relations = db.query(Relation).filter(Relation.case_id == case.id).all()
        print(f"Deleting {len(relations)} relations for CASE-002...")
        for rel in relations:
            db.delete(rel)
        db.flush()

        # 5. Events & Participants
        events = db.query(Event).filter(Event.case_id == case.id).all()
        event_ids = [ev.id for ev in events]
        if event_ids:
            participants = db.query(EventParticipant).filter(EventParticipant.event_id.in_(event_ids)).all()
            print(f"Deleting {len(participants)} event participants for CASE-002...")
            for p in participants:
                db.delete(p)
            db.flush()

        print(f"Deleting {len(events)} events for CASE-002...")
        for ev in events:
            db.delete(ev)
        db.flush()

        # 6. Mentions deletion
        if mentions:
            print(f"Deleting {len(mentions)} entity mentions for CASE-002...")
            for m in mentions:
                db.delete(m)
            db.flush()

        # 7. Entities
        entities = db.query(Entity).filter(Entity.case_id == case.id).all()
        print(f"Deleting {len(entities)} canonical entities for CASE-002...")
        for ent in entities:
            db.delete(ent)
        db.flush()

        # 8. Evidence Integrity
        if evidence_ids:
            integrities = db.query(EvidenceIntegrity).filter(EvidenceIntegrity.evidence_id.in_(evidence_ids)).all()
            print(f"Deleting {len(integrities)} integrity records for CASE-002...")
            for integ in integrities:
                db.delete(integ)
            db.flush()

        # 9. Evidence
        print(f"Deleting {len(evidence_list)} evidence records for CASE-002...")
        for ev in evidence_list:
            db.delete(ev)
        db.flush()

        db.commit()
        print("\n=== CASE-002 CLEANUP COMPLETED ===")
        print(f"Evidence count: {db.query(Evidence).filter(Evidence.case_id == case.id).count()}")
        print(f"Entities count: {db.query(Entity).filter(Entity.case_id == case.id).count()}")
        print(f"Relations count: {db.query(Relation).filter(Relation.case_id == case.id).count()}")
        print(f"Events count: {db.query(Event).filter(Event.case_id == case.id).count()}")

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    clean_case_002()
