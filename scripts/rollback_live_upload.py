import sys
import shutil
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import select, func, or_, delete
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
from app.graph import build_case_graph
from app.neo4j_projection import rebuild_projection
from app.storage import STORAGE_ROOT

CANONICAL_CASE_002_EVIDENCE_IDS = {
    "EVD-002-FIR01",
    "EVD-002-CDR01",
    "EVD-002-FIN01",
    "EVD-002-SURV01",
    "EVD-002-INTEL01",
    "EVD-002-VEH01",
}

def get_counts(db, case_id):
    ev_count = db.scalar(select(func.count()).select_from(Evidence).where(Evidence.case_id == case_id))
    ent_count = db.scalar(select(func.count()).select_from(Entity).where(Entity.case_id == case_id))
    
    ev_ids = db.scalars(select(Evidence.id).where(Evidence.case_id == case_id)).all()
    mention_count = db.scalar(select(func.count()).select_from(EntityMentionRecord).where(EntityMentionRecord.evidence_id.in_(ev_ids))) if ev_ids else 0
    mention_ids = db.scalars(select(EntityMentionRecord.id).where(EntityMentionRecord.evidence_id.in_(ev_ids))).all() if ev_ids else []
    
    resol_count = 0
    if mention_ids:
        resol_count = db.scalar(
            select(func.count()).select_from(EntityResolution).where(
                or_(
                    EntityResolution.source_mention_id.in_(mention_ids),
                    EntityResolution.target_mention_id.in_(mention_ids),
                )
            )
        )
    
    rel_count = db.scalar(select(func.count()).select_from(Relation).where(Relation.case_id == case_id))
    event_count = db.scalar(select(func.count()).select_from(Event).where(Event.case_id == case_id))
    integ_count = db.scalar(select(func.count()).select_from(EvidenceIntegrity).where(EvidenceIntegrity.evidence_id.in_(ev_ids))) if ev_ids else 0
    flag_count = db.scalar(select(func.count()).select_from(InvestigationFlag).where(InvestigationFlag.case_id == case_id))
    
    return {
        "evidence": ev_count,
        "entities": ent_count,
        "mentions": mention_count,
        "relations": rel_count,
        "events": event_count,
        "resolutions": resol_count,
        "integrity": integ_count,
        "flags": flag_count,
    }

def rollback_evidence(target_query: str = None):
    db = SessionLocal()
    try:
        print("=" * 80)
        print("UNIVERSAL ROLLBACK TOOL FOR ACCIDENTAL EVIDENCE UPLOADS")
        print("=" * 80)

        c1 = db.scalar(select(Case).where(Case.case_number == "CASE-001"))
        c2 = db.scalar(select(Case).where(Case.case_number == "CASE-002"))
        c3 = db.scalar(select(Case).where(Case.case_number == "CASE-003"))

        if not c2:
            print("ERROR: CASE-002 not found in database.")
            return

        c1_before = get_counts(db, c1.id) if c1 else {}
        c2_before = get_counts(db, c2.id)
        c3_before = get_counts(db, c3.id) if c3 else {}

        print("\n--- SNAPSHOT COUNTS BEFORE ROLLBACK ---")
        print(f"CASE-001: {c1_before}")
        print(f"CASE-002: {c2_before}")
        print(f"CASE-003: {c3_before}")

        # Find target evidence records to rollback
        if target_query:
            target_ev_list = db.scalars(
                select(Evidence).where(
                    (Evidence.case_id == c2.id) &
                    (
                        (Evidence.evidence_id == target_query) |
                        (Evidence.filename == target_query) |
                        (Evidence.evidence_id.ilike(f"%{target_query}%")) |
                        (Evidence.filename.ilike(f"%{target_query}%"))
                    )
                )
            ).all()
        else:
            # Automatically find any non-canonical evidence in CASE-002
            target_ev_list = db.scalars(
                select(Evidence).where(
                    (Evidence.case_id == c2.id) &
                    (Evidence.evidence_id.not_in(CANONICAL_CASE_002_EVIDENCE_IDS))
                )
            ).all()

        if not target_ev_list:
            print(f"\nNo target evidence found matching '{target_query or 'non-canonical'}' in CASE-002.")
            print("CASE-002 already has only canonical evidence.")
            return

        for target_ev in target_ev_list:
            target_ev_id = target_ev.id
            target_evidence_id_str = target_ev.evidence_id
            target_filename = target_ev.filename
            print(f"\n>>> PROCESSING ROLLBACK FOR: {target_evidence_id_str} ({target_filename}) <<<")

            # 1. Mentions
            target_mentions = db.scalars(
                select(EntityMentionRecord).where(EntityMentionRecord.evidence_id == target_ev_id)
            ).all()
            target_mention_ids = [m.id for m in target_mentions]
            print(f"  Found {len(target_mentions)} mentions created exclusively by this evidence.")

            # 2. Resolutions involving upload mentions
            if target_mention_ids:
                del_res_stmt = delete(EntityResolution).where(
                    or_(
                        EntityResolution.source_mention_id.in_(target_mention_ids),
                        EntityResolution.target_mention_id.in_(target_mention_ids),
                    )
                )
                del_res_result = db.execute(del_res_stmt)
                print(f"  Deleted {del_res_result.rowcount} entity resolution records involving upload mentions.")

            # 3. Relations originating from this evidence or its mentions
            del_rel_stmt = delete(Relation).where(
                or_(
                    Relation.evidence_id == target_ev_id,
                    Relation.source_mention_id.in_(target_mention_ids) if target_mention_ids else False,
                    Relation.target_mention_id.in_(target_mention_ids) if target_mention_ids else False,
                )
            )
            del_rel_result = db.execute(del_rel_stmt)
            print(f"  Deleted {del_rel_result.rowcount} relations originating from this upload.")

            # 4. Events & EventParticipants
            target_events = db.scalars(select(Event).where(Event.evidence_id == target_ev_id)).all()
            target_event_ids = [ev.id for ev in target_events]
            if target_event_ids:
                del_parts = db.execute(delete(EventParticipant).where(EventParticipant.event_id.in_(target_event_ids)))
                print(f"  Deleted {del_parts.rowcount} event participants.")
                del_evs = db.execute(delete(Event).where(Event.id.in_(target_event_ids)))
                print(f"  Deleted {del_evs.rowcount} events.")

            # 5. Entities: Check Category B (exclusive to upload) vs Category C (shared)
            exclusive_entities_deleted = []
            shared_entities_preserved = []

            for mention in target_mentions:
                if not mention.entity_id:
                    continue
                ent = db.scalar(select(Entity).where(Entity.id == mention.entity_id))
                if not ent:
                    continue
                
                # Check if this entity has any other mentions outside target_mention_ids
                other_mentions_count = db.scalar(
                    select(func.count()).select_from(EntityMentionRecord).where(
                        (EntityMentionRecord.entity_id == ent.id) &
                        (EntityMentionRecord.id.not_in(target_mention_ids))
                    )
                )
                
                if other_mentions_count == 0:
                    if ent.id not in [e["id"] for e in exclusive_entities_deleted]:
                        exclusive_entities_deleted.append({
                            "id": ent.id,
                            "canonical_name": ent.canonical_name,
                            "entity_type": ent.entity_type
                        })
                        db.delete(ent)
                else:
                    if ent.id not in [e["id"] for e in shared_entities_preserved]:
                        shared_entities_preserved.append({
                            "id": ent.id,
                            "canonical_name": ent.canonical_name,
                            "entity_type": ent.entity_type,
                            "remaining_mentions": other_mentions_count
                        })

            print(f"  Removed {len(exclusive_entities_deleted)} exclusive orphan entities (Category B).")
            print(f"  Safely preserved {len(shared_entities_preserved)} shared canonical entities (Category C).")

            # 6. Delete entity mentions for this evidence
            if target_mention_ids:
                del_m = db.execute(delete(EntityMentionRecord).where(EntityMentionRecord.id.in_(target_mention_ids)))
                print(f"  Deleted {del_m.rowcount} entity mentions.")

            # 7. Delete integrity records
            del_integ = db.execute(delete(EvidenceIntegrity).where(EvidenceIntegrity.evidence_id == target_ev_id))
            print(f"  Deleted {del_integ.rowcount} integrity records.")

            # 8. Delete flags on this evidence if any
            del_flags = db.execute(
                delete(InvestigationFlag).where(
                    (InvestigationFlag.case_id == c2.id) &
                    (
                        (InvestigationFlag.resource_id == target_evidence_id_str) |
                        (InvestigationFlag.resource_id == str(target_ev_id)) |
                        (InvestigationFlag.resource_label.ilike(f"%{target_evidence_id_str}%")) |
                        (InvestigationFlag.resource_label.ilike(f"%{target_filename}%"))
                    )
                )
            )
            print(f"  Deleted {del_flags.rowcount} investigation flags on this evidence.")

            # 9. Delete upload-related audit events
            del_aud = db.execute(
                delete(AuditEvent).where(
                    or_(
                        AuditEvent.resource_id == str(target_ev_id),
                        AuditEvent.resource_id == target_evidence_id_str,
                        AuditEvent.resource_id.ilike(f"%{target_evidence_id_str}%"),
                    )
                )
            )
            print(f"  Deleted {del_aud.rowcount} audit events.")

            # 10. Delete physical storage directory
            storage_path = STORAGE_ROOT / target_evidence_id_str
            if storage_path.exists() and storage_path.is_dir():
                shutil.rmtree(storage_path)
                print(f"  Deleted physical storage directory: {storage_path}")
            else:
                print(f"  Storage directory does not exist or already removed: {storage_path}")

            # 11. Delete Evidence record
            db.delete(target_ev)
            db.commit()
            print(f"  Deleted evidence record {target_evidence_id_str} and committed transaction.")

        # 12. Rebuild Neo4j Knowledge Graph Projection for CASE-002
        print("\nRebuilding Neo4j graph projection for clean state...")
        graph = build_case_graph(db, c2)
        proj_res = rebuild_projection(graph)
        print(f"Neo4j projection result: {proj_res}")

        # Snapshot AFTER
        c1_after = get_counts(db, c1.id) if c1 else {}
        c2_after = get_counts(db, c2.id)
        c3_after = get_counts(db, c3.id) if c3 else {}

        print("\n" + "=" * 80)
        print("SNAPSHOT COUNTS AFTER ROLLBACK")
        print("=" * 80)
        print(f"CASE-001: {c1_after}")
        print(f"CASE-002: {c2_after}")
        print(f"CASE-003: {c3_after}")

        # Check remaining evidence in CASE-002
        remaining_evs = db.scalars(select(Evidence).where(Evidence.case_id == c2.id).order_by(Evidence.uploaded_at)).all()
        print(f"\nRemaining Evidence in CASE-002 ({len(remaining_evs)} total):")
        for e in remaining_evs:
            print(f"  - {e.evidence_id}: {e.filename} ({e.document_type})")

        # Check remaining entity resolutions in CASE-002
        c2_all_ev_ids = [e.id for e in remaining_evs]
        c2_mentions = db.scalars(select(EntityMentionRecord.id).where(EntityMentionRecord.evidence_id.in_(c2_all_ev_ids))).all()
        c2_resolutions = db.scalars(
            select(EntityResolution).where(
                EntityResolution.source_mention_id.in_(c2_mentions) &
                EntityResolution.target_mention_id.in_(c2_mentions)
            )
        ).all()
        print(f"\nRemaining Entity Resolutions in CASE-002 ({len(c2_resolutions)} total):")
        for r in c2_resolutions:
            sm = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.id == r.source_mention_id))
            tm = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.id == r.target_mention_id))
            print(f"  - '{sm.text if sm else '?'}' <-> '{tm.text if tm else '?'}' | Status: {r.status} | Conf: {r.confidence}")

        print("\nRollback completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"ERROR DURING ROLLBACK: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else None
    rollback_evidence(query)
