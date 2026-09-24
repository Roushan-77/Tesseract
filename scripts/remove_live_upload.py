import sys
import shutil
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import select, delete, or_
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
)
from app.neo4j_projection import rebuild_projection
from app.storage import STORAGE_ROOT

def remove_live_upload():
    db = SessionLocal()
    try:
        c2 = db.scalar(select(Case).where(Case.case_number == "CASE-002"))
        if not c2:
            print("CASE-002 not found.")
            return

        # Find live uploaded document(s)
        live_evidence_list = db.scalars(
            select(Evidence).where(
                (Evidence.case_id == c2.id) &
                (
                    (Evidence.filename == "Live-Field-Verification.pdf") |
                    (Evidence.evidence_id == "EVD-002-E4FC4EE3") |
                    (Evidence.filename.ilike("%Live%"))
                )
            )
        ).all()

        if not live_evidence_list:
            print("No Live-Field-Verification.pdf evidence found in CASE-002. Already clean.")
            return

        for live_ev in live_evidence_list:
            print(f"Removing live evidence: {live_ev.evidence_id} ({live_ev.filename})...")
            live_ev_id = live_ev.id
            live_evidence_id_str = live_ev.evidence_id

            # 1. Get mentions for this live evidence
            live_mentions = db.scalars(
                select(EntityMentionRecord).where(EntityMentionRecord.evidence_id == live_ev_id)
            ).all()
            live_mention_ids = [m.id for m in live_mentions]
            print(f"  Found {len(live_mention_ids)} mentions associated with {live_evidence_id_str}.")

            # 2. Delete resolutions involving these mentions
            if live_mention_ids:
                del_resols = db.execute(
                    delete(EntityResolution).where(
                        or_(
                            EntityResolution.source_mention_id.in_(live_mention_ids),
                            EntityResolution.target_mention_id.in_(live_mention_ids),
                        )
                    )
                )
                print(f"  Deleted {del_resols.rowcount} entity resolutions involving live mentions.")

            # 3. Delete relations originating from this evidence or involving its mentions
            del_rels = db.execute(
                delete(Relation).where(
                    or_(
                        Relation.evidence_id == live_ev_id,
                        Relation.source_mention_id.in_(live_mention_ids) if live_mention_ids else False,
                        Relation.target_mention_id.in_(live_mention_ids) if live_mention_ids else False,
                    )
                )
            )
            print(f"  Deleted {del_rels.rowcount} relations originating from {live_evidence_id_str}.")

            # 4. Delete events and participants for this evidence
            live_events = db.scalars(select(Event).where(Event.evidence_id == live_ev_id)).all()
            live_event_ids = [ev.id for ev in live_events]
            if live_event_ids:
                del_parts = db.execute(
                    delete(EventParticipant).where(EventParticipant.event_id.in_(live_event_ids))
                )
                print(f"  Deleted {del_parts.rowcount} event participants.")
                del_evs = db.execute(
                    delete(Event).where(Event.id.in_(live_event_ids))
                )
                print(f"  Deleted {del_evs.rowcount} events.")

            # 5. Check if any canonical entity was solely created by this live upload and has no other mentions
            for mention in live_mentions:
                if mention.entity_id:
                    other_mentions_count = db.scalar(
                        select(EntityMentionRecord)
                        .where(
                            (EntityMentionRecord.entity_id == mention.entity_id) &
                            (EntityMentionRecord.id.not_in(live_mention_ids))
                        )
                    )
                    if not other_mentions_count:
                        # Solely created by this live document
                        entity_to_del = db.scalar(select(Entity).where(Entity.id == mention.entity_id))
                        if entity_to_del:
                            print(f"  Deleting orphan entity solely from live doc: {entity_to_del.canonical_name} ({entity_to_del.entity_type})")
                            db.delete(entity_to_del)

            # 6. Delete mentions
            if live_mention_ids:
                del_m = db.execute(
                    delete(EntityMentionRecord).where(EntityMentionRecord.id.in_(live_mention_ids))
                )
                print(f"  Deleted {del_m.rowcount} entity mentions.")

            # 7. Delete integrity records
            del_integ = db.execute(
                delete(EvidenceIntegrity).where(EvidenceIntegrity.evidence_id == live_ev_id)
            )
            print(f"  Deleted {del_integ.rowcount} integrity records.")

            # 8. Delete audit events for this evidence
            del_aud = db.execute(
                delete(AuditEvent).where(
                    or_(
                        AuditEvent.resource_id == str(live_ev_id),
                        AuditEvent.resource_id == live_evidence_id_str,
                    )
                )
            )
            print(f"  Deleted {del_aud.rowcount} audit events.")

            # 9. Delete physical storage folder
            storage_path = STORAGE_ROOT / live_evidence_id_str
            if storage_path.exists() and storage_path.is_dir():
                shutil.rmtree(storage_path)
                print(f"  Deleted physical storage folder: {storage_path}")

            # 10. Delete evidence record
            db.delete(live_ev)
            db.commit()
            print(f"  Deleted evidence record {live_evidence_id_str} successfully.")

        # 11. Re-project Neo4j knowledge graph
        print("Re-projecting Neo4j knowledge graph...")
        rebuild_projection(db)
        print("Neo4j projection rebuilt successfully.")

        # Verification check
        remaining_evs = db.scalars(select(Evidence).where(Evidence.case_id == c2.id)).all()
        print(f"\nVerification: CASE-002 currently has {len(remaining_evs)} evidence files:")
        for e in remaining_evs:
            print(f"  - {e.evidence_id}: {e.filename} ({e.document_type})")

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    remove_live_upload()
