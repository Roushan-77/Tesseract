import os
import sys
from pathlib import Path

# Add apps/api to path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "apps" / "api"))
sys.stdout.reconfigure(encoding='utf-8')

from app.database import SessionLocal
from app.models import Case, Evidence, Entity, EntityResolution, Relation, Event, User, EntityMentionRecord
from app.graph import build_case_graph, intelligence_for_case, timeline_for_case
from app.access import has_case_access

def verify():
    db = SessionLocal()
    try:
        c1 = db.query(Case).filter(Case.case_number == 'CASE-001').first()
        c2 = db.query(Case).filter(Case.case_number == 'CASE-002').first()
        c3 = db.query(Case).filter(Case.case_number == 'CASE-003').first()
        u_rahul = db.query(User).filter(User.investigator_id == 'INV-017').first()
        u_ananya = db.query(User).filter(User.investigator_id == 'INV-021').first()

        print("==================================================")
        print("1. CASE-001 STATUS (Indore Transport Network)")
        print("==================================================")
        print(f"Case ID: {c1.case_number} | Title: {c1.title}")
        print(f"Evidence Count: {db.query(Evidence).filter(Evidence.case_id == c1.id).count()}")
        print(f"Entities Count: {db.query(Entity).filter(Entity.case_id == c1.id).count()}")
        print(f"Relations Count: {db.query(Relation).filter(Relation.case_id == c1.id).count()}")
        print(f"Timeline Events: {len(timeline_for_case(db, c1))}")

        print("\n==================================================")
        print("2. CASE-002 STATUS (Mumbai Warehouse Network)")
        print("==================================================")
        print(f"Case ID: {c2.case_number} | Title: {c2.title}")
        evs = db.query(Evidence).filter(Evidence.case_id == c2.id).all()
        print(f"Evidence Count: {len(evs)}")
        for e in evs:
            print(f"  - [{e.evidence_id}] {e.filename} ({e.document_type} | {e.ingestion_method} | Integrity: {e.integrity_status})")

        ents = db.query(Entity).filter(Entity.case_id == c2.id).all()
        print(f"\nEntities Count: {len(ents)}")
        for ent in ents:
            print(f"  - [{ent.entity_type}] {ent.canonical_name}")

        resolutions = db.query(EntityResolution).join(EntityMentionRecord, EntityResolution.source_mention_id == EntityMentionRecord.id).filter(EntityMentionRecord.evidence.has(case_id=c2.id)).all()
        print(f"\nHuman-in-the-Loop Review Candidates: {len(resolutions)}")
        for r in resolutions:
            src_m = db.get(EntityMentionRecord, r.source_mention_id)
            tgt_m = db.get(EntityMentionRecord, r.target_mention_id)
            print(f"  - '{src_m.text}' <-> '{tgt_m.text}' | Confidence: {int(r.confidence*100)}% | Status: {r.status}")
            print(f"    Reasons: {r.reasons}")

        graph = build_case_graph(db, c2)
        print(f"\nGraph Node Count: {len(graph['nodes'])} | Edge Count: {len(graph['edges'])}")

        intel = intelligence_for_case(db, c2)
        print(f"\nIntelligence Findings ({len(intel['findings'])}):")
        for f in intel['findings']:
            print(f"  - [{f['type']}] {f['title']}")
            print(f"    Explanation: {f['explanation']}")
            print(f"    Evidence: {f.get('evidenceIds')}")

        events = timeline_for_case(db, c2)
        print(f"\nTimeline Events Count: {len(events)}")
        for ev in events:
            print(f"  - {ev['date']} {ev['time']} [{ev['type']}] {ev['sourceText'][:75]}...")

        print("\n==================================================")
        print("3. CASE-003 RESTRICTED STATUS")
        print("==================================================")
        print(f"Case ID: {c3.case_number} | Title: {c3.title}")
        print(f"Evidence Count in DB: {db.query(Evidence).filter(Evidence.case_id == c3.id).count()}")
        print(f"Lead Investigator: {c3.lead_investigator.name} ({c3.lead_investigator.investigator_id})")
        print(f"Investigator Rahul (INV-017) has access: {has_case_access(db, u_rahul, c3)}")
        print(f"Lead Ananya (INV-021) has access: {has_case_access(db, u_ananya, c3)}")

        print("\n==================================================")
        print("4. STANDALONE DATASET FILES")
        print("==================================================")
        c2_files = list((BASE_DIR / "seed" / "demo" / "final-case-002").iterdir())
        print(f"CASE-002 folder ({len(c2_files)} items): {[f.name for f in c2_files]}")
        c3_files = list((BASE_DIR / "seed" / "demo" / "final-case-003").iterdir())
        print(f"CASE-003 folder ({len(c3_files)} items): {[f.name for f in c3_files]}")
        live_pdf = BASE_DIR / "seed" / "demo" / "Live-Field-Verification.pdf"
        print(f"Live PDF file ready on disk: {live_pdf.exists()} ({live_pdf.stat().st_size if live_pdf.exists() else 0} bytes)")

    finally:
        db.close()

if __name__ == "__main__":
    verify()
