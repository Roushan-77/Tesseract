import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import select, func, or_
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
    InvestigationFlag,
)
from app.storage import STORAGE_ROOT

def inspect():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("DATABASE INSPECTION BEFORE ROLLBACK")
        print("=" * 60)

        # 1. Cases overview
        cases = db.scalars(select(Case).order_by(Case.case_number)).all()
        for c in cases:
            ev_count = db.scalar(select(func.count()).select_from(Evidence).where(Evidence.case_id == c.id))
            ent_count = db.scalar(select(func.count()).select_from(Entity).where(Entity.case_id == c.id))
            rel_count = db.scalar(select(func.count()).select_from(Relation).where(Relation.case_id == c.id))
            evts_count = db.scalar(select(func.count()).select_from(Event).where(Event.case_id == c.id))
            flags_count = db.scalar(select(func.count()).select_from(InvestigationFlag).where(InvestigationFlag.case_id == c.id))
            print(f"Case: {c.case_number} ({c.title})")
            print(f"  Evidence count: {ev_count}")
            print(f"  Entity count: {ent_count}")
            print(f"  Relation count: {rel_count}")
            print(f"  Event count: {evts_count}")
            print(f"  Flag count: {flags_count}")

        print("\n" + "-" * 60)
        c2 = db.scalar(select(Case).where(Case.case_number == "CASE-002"))
        if not c2:
            print("CASE-002 not found!")
            return

        # 2. Evidence in CASE-002
        c2_evidences = db.scalars(select(Evidence).where(Evidence.case_id == c2.id).order_by(Evidence.uploaded_at)).all()
        print(f"CASE-002 Evidence List ({len(c2_evidences)} total):")
        target_ev = None
        for ev in c2_evidences:
            is_target = (
                ev.evidence_id == "EVD-002-E17DF93E" or 
                ev.filename == "Live-Field-Verification.pdf" or 
                "Live" in ev.filename or 
                "E17DF93E" in ev.evidence_id
            )
            marker = " *** [TARGET FOR ROLLBACK] ***" if is_target else ""
            print(f"  - ID: {ev.evidence_id} | Name: {ev.filename} | Type: {ev.document_type} | Uploaded: {ev.uploaded_at}{marker}")
            if is_target:
                target_ev = ev

        if not target_ev:
            print("\nTarget evidence EVD-002-E17DF93E / Live-Field-Verification.pdf NOT FOUND in database.")
            # Let's check across all cases just in case
            all_target = db.scalars(select(Evidence).where(
                or_(
                    Evidence.evidence_id.ilike("%E17DF93E%"),
                    Evidence.filename.ilike("%Live-Field%"),
                )
            )).all()
            print(f"Search across all cases found: {len(all_target)} records")
            for te in all_target:
                print(f"  Found in case_id {te.case_id}: {te.evidence_id} - {te.filename}")
            return

        print("\n" + "=" * 60)
        print(f"TARGET EVIDENCE DETAILS: {target_ev.evidence_id} ({target_ev.filename})")
        print("=" * 60)

        # Mentions from this evidence
        target_mentions = db.scalars(
            select(EntityMentionRecord).where(EntityMentionRecord.evidence_id == target_ev.id)
        ).all()
        target_mention_ids = [m.id for m in target_mentions]
        print(f"\n1. Mentions created by this evidence ({len(target_mentions)} total):")
        for m in target_mentions:
            ent = db.scalar(select(Entity).where(Entity.id == m.entity_id)) if m.entity_id else None
            ent_name = ent.canonical_name if ent else "UNRESOLVED/NO_ENTITY"
            print(f"  - Mention: '{m.text}' -> Normalized: '{m.normalized_value}' ({m.entity_type}) | Entity: {ent_name} (ID: {m.entity_id})")

        # Check Entities associated with these mentions: are they exclusive or shared?
        print("\n2. Entity Classification (Exclusive to Upload vs Shared with Pre-existing):")
        for m in target_mentions:
            if not m.entity_id:
                continue
            ent = db.scalar(select(Entity).where(Entity.id == m.entity_id))
            if not ent:
                continue
            
            # Count other mentions for this entity NOT in target_mention_ids
            other_mentions = db.scalars(
                select(EntityMentionRecord).where(
                    (EntityMentionRecord.entity_id == ent.id) &
                    (EntityMentionRecord.id.not_in(target_mention_ids))
                )
            ).all()
            
            if len(other_mentions) == 0:
                print(f"  - EXCLUSIVE (Category B - TO DELETE): Entity {ent.canonical_name} ({ent.entity_type}, ID: {ent.id}) has ONLY mentions from this upload.")
            else:
                other_ev_ids = {om.evidence_id for om in other_mentions}
                other_evs = db.scalars(select(Evidence).where(Evidence.id.in_(other_ev_ids))).all()
                other_filenames = [oe.filename for oe in other_evs]
                print(f"  - SHARED (Category C - MUST PRESERVE CANONICAL): Entity {ent.canonical_name} ({ent.entity_type}, ID: {ent.id}) is also referenced by {len(other_mentions)} mentions in: {', '.join(other_filenames)}")

        # Relations created by or involving this evidence / mentions
        target_relations = db.scalars(
            select(Relation).where(
                or_(
                    Relation.evidence_id == target_ev.id,
                    Relation.source_mention_id.in_(target_mention_ids) if target_mention_ids else False,
                    Relation.target_mention_id.in_(target_mention_ids) if target_mention_ids else False,
                )
            )
        ).all()
        print(f"\n3. Relations created by this evidence ({len(target_relations)} total):")
        for r in target_relations:
            src_ent = db.scalar(select(Entity).where(Entity.id == r.source_entity_id)) if r.source_entity_id else None
            tgt_ent = db.scalar(select(Entity).where(Entity.id == r.target_entity_id)) if r.target_entity_id else None
            print(f"  - Relation: {src_ent.canonical_name if src_ent else r.source_text} --[{r.relation_type}]--> {tgt_ent.canonical_name if tgt_ent else '?'} | Confidence: {r.confidence}")

        # Events created by this evidence
        target_events = db.scalars(
            select(Event).where(Event.evidence_id == target_ev.id)
        ).all()
        print(f"\n4. Events created by this evidence ({len(target_events)} total):")
        for ev_item in target_events:
            print(f"  - Event: [{ev_item.event_type}] {ev_item.event_date} {ev_item.event_time} - {ev_item.source_text}")

        # Entity Resolutions involving target mentions
        target_resolutions = []
        if target_mention_ids:
            target_resolutions = db.scalars(
                select(EntityResolution).where(
                    or_(
                        EntityResolution.source_mention_id.in_(target_mention_ids),
                        EntityResolution.target_mention_id.in_(target_mention_ids),
                    )
                )
            ).all()
        print(f"\n5. Entity Resolutions involving upload mentions ({len(target_resolutions)} total):")
        for res in target_resolutions:
            sm = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.id == res.source_mention_id))
            tm = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.id == res.target_mention_id))
            print(f"  - Resolution: '{sm.text if sm else '?'}' <-> '{tm.text if tm else '?'}' | Status: {res.status} | Conf: {res.confidence}")

        # Pre-existing entity resolutions in CASE-002 not involving target mentions
        c2_all_ev_ids = [e.id for e in c2_evidences if e.id != target_ev.id]
        c2_existing_mentions = db.scalars(
            select(EntityMentionRecord).where(EntityMentionRecord.evidence_id.in_(c2_all_ev_ids))
        ).all()
        c2_existing_mention_ids = [m.id for m in c2_existing_mentions]
        c2_existing_resolutions = db.scalars(
            select(EntityResolution).where(
                EntityResolution.source_mention_id.in_(c2_existing_mention_ids) &
                EntityResolution.target_mention_id.in_(c2_existing_mention_ids)
            )
        ).all()
        print(f"\n   -> Pre-existing CASE-002 entity resolutions to preserve ({len(c2_existing_resolutions)} total):")
        for pres in c2_existing_resolutions:
            sm = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.id == pres.source_mention_id))
            tm = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.id == pres.target_mention_id))
            print(f"      * '{sm.text if sm else '?'}' <-> '{tm.text if tm else '?'}' | Status: {pres.status}")

        # Integrity record
        integrity_records = db.scalars(
            select(EvidenceIntegrity).where(EvidenceIntegrity.evidence_id == target_ev.id)
        ).all()
        print(f"\n6. Evidence Integrity records ({len(integrity_records)} total):")
        for integ in integrity_records:
            print(f"  - SHA256: {integ.sha256} | Ledger: {integ.ledger_record_id} | Status: {integ.registration_status}")

        # Flags on this evidence or created by this evidence
        target_flags = db.scalars(
            select(InvestigationFlag).where(
                (InvestigationFlag.case_id == c2.id) &
                (
                    (InvestigationFlag.resource_id == target_ev.evidence_id) |
                    (InvestigationFlag.resource_id == str(target_ev.id)) |
                    (InvestigationFlag.resource_label.ilike(f"%{target_ev.filename}%"))
                )
            )
        ).all()
        print(f"\n7. Investigation Flags on this evidence ({len(target_flags)} total):")
        for fl in target_flags:
            print(f"  - Flag: [{fl.resource_type}] {fl.resource_label} | Reason: {fl.reason} | Status: {fl.status}")

        # Audit events
        audit_events = db.scalars(
            select(AuditEvent).where(
                or_(
                    AuditEvent.resource_id == str(target_ev.id),
                    AuditEvent.resource_id == target_ev.evidence_id,
                    AuditEvent.resource_id.ilike(f"%{target_ev.evidence_id}%"),
                )
            )
        ).all()
        print(f"\n8. Audit Events ({len(audit_events)} total):")
        for ae in audit_events:
            print(f"  - Action: {ae.action} | Resource: {ae.resource_type} ({ae.resource_id}) | Time: {ae.timestamp}")

        # Disk storage
        storage_path = STORAGE_ROOT / target_ev.evidence_id
        print(f"\n9. Disk Storage Path: {storage_path} (Exists: {storage_path.exists()})")

    finally:
        db.close()

if __name__ == "__main__":
    inspect()
