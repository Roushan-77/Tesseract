import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from .config import settings
from .database import SessionLocal
from .models import (
    AuditEvent,
    Case,
    CaseAssignment,
    Entity,
    EntityMentionRecord,
    EntityResolution,
    Event,
    EventParticipant,
    Evidence,
    EvidenceIntegrity,
    Relation,
    User,
    now,
    uid,
)
from .storage import STORAGE_ROOT

BASE_DIR = Path(__file__).resolve().parents[3]
CASE_002_SRC = BASE_DIR / "seed" / "demo" / "final-case-002"

EVIDENCE_DATA_CASE_001 = [
    {
        "evidence_id": "EVD-001-FIR01",
        "filename": "FIR-402-Indore.txt",
        "document_type": "TXT",
        "mime_type": "text/plain",
        "document_language": "en",
        "notes": "First Information Report registered at Pithampur Police Station regarding unauthorized consignment diversion.",
        "content": """FIRST INFORMATION REPORT (FIR NO. 402/2026)
Police Station: Pithampur Industrial Area, Sector 3
District: Dhar / Indore Region, Madhya Pradesh
Date of Registration: 04-June-2026

COMPLAINANT / INFORMANT:
Station Duty Officer, Pithampur Sub-Division.

DETAILS OF INCIDENT:
A formal inquiry was initiated following reports of systematic consignment discrepancies originating from the Pithampur Industrial Hub. Freight shipments logged under Malwa Freight Carriers were discovered to have been diverted from designated highway transit routes toward unauthorized commercial storage units in Dewas Naka Depot.

Preliminary documentation implicates Logistics Operations Manager Rajesh Verma and fleet coordinator Sunil Deshmukh in the unauthorized alteration of dispatch manifests. Commercial carrier vehicle MP-09-AB-4412 was identified in several unrecorded freight diversions.

STATUS: Active Investigation under relevant sections of IPC and Motor Vehicles Act.
""",
    },
    {
        "evidence_id": "EVD-001-CDR01",
        "filename": "CDR-Indore-Jun2026.csv",
        "document_type": "CSV",
        "mime_type": "text/csv",
        "document_language": "en",
        "notes": "Telecommunication CDR logs showing communication activity escalation between target phone numbers.",
        "content": """timestamp,caller,receiver,duration,cell_tower
2026-06-02T21:15:00,+91-98260-11223,+91-94250-99881,180,Indore-Tower-04
2026-06-06T19:40:00,+91-98260-11223,+91-94250-99881,120,Indore-Tower-04
2026-06-12T10:32:00,+91-98260-11223,+91-94250-99881,245,Indore-Tower-04
2026-06-12T10:48:00,+91-98260-11223,+91-94250-99881,95,Indore-Tower-04
2026-06-12T14:15:00,+91-94250-99881,+91-98260-11223,310,Indore-Tower-04
2026-06-13T09:20:00,+91-98260-11223,+91-94250-99881,160,Indore-Tower-04
2026-06-13T16:05:00,+91-94250-99881,+91-98260-11223,280,Indore-Tower-04
2026-06-13T21:50:00,+91-98260-11223,+91-94250-99881,420,Indore-Tower-11
2026-06-14T08:10:00,+91-98260-11223,+91-94250-99881,190,Indore-Tower-04
2026-06-14T11:30:00,+91-94250-99881,+91-98260-11223,135,Indore-Tower-04
2026-06-14T15:45:00,+91-98260-11223,+91-94250-99881,215,Indore-Tower-04
2026-06-14T19:00:00,+91-98260-11223,+91-94250-99881,380,Indore-Tower-11
2026-06-14T23:12:00,+91-94250-99881,+91-98260-11223,290,Indore-Tower-11
2026-06-18T22:45:00,+91-98260-11223,+91-94250-99881,512,Indore-Tower-11
""",
    },
    {
        "evidence_id": "EVD-001-FIN01",
        "filename": "Bank-Transfer-Ledger.csv",
        "document_type": "CSV",
        "mime_type": "text/csv",
        "document_language": "en",
        "notes": "Corporate bank transaction ledger of Malwa Freight Carriers reflecting baseline vs anomalous disbursements.",
        "content": """timestamp,sender_account,receiver_account,amount,transaction_id,location,remarks
2026-06-01T10:15:00,MFC-CORP-9021,SUP-OIL-1002,32500,TXN-20260601-1001,Indore Main Branch,Routine fuel advance
2026-06-04T14:30:00,MFC-CORP-9021,TYRE-IND-8812,45000,TXN-20260604-2041,Indore Main Branch,Fleet maintenance
2026-06-08T11:00:00,MFC-CORP-9021,DRV-WAGE-4401,28000,TXN-20260608-3012,Indore Main Branch,Driver weekly stipend
2026-06-12T11:45:00,MFC-CORP-9021,AS-IND-4410,480000,TXN-20260612-9901,Indore Main Branch,Expedited freight clearance (Anomalous)
2026-06-16T16:20:00,MFC-CORP-9021,TOLL-FAST-9090,35000,TXN-20260616-4109,Indore Main Branch,National highway toll recharge
2026-06-20T10:45:00,MFC-CORP-9021,WH-RENT-3312,42000,TXN-20260620-5501,Indore Main Branch,Warehouse facility lease
""",
    },
    {
        "evidence_id": "EVD-001-SURV01",
        "filename": "Surveillance-Field-Log.txt",
        "document_type": "TXT",
        "mime_type": "text/plain",
        "document_language": "en",
        "notes": "Field surveillance observation log from Crime Branch team monitoring Vijay Nagar Warehouse.",
        "content": """CRIME BRANCH INDORE — FIELD SURVEILLANCE LOG
Target Location: Vijay Nagar Warehouse, Indore (Plot 44-B, Industrial Estate)
Monitoring Team: Sub-Inspector Ananya Sharma & Surveillance Unit 2

LOG ENTRIES:

[2026-06-10 13:45] Surveillance post established opposite Vijay Nagar Warehouse, Indore.
[2026-06-10 14:00] Subject Rajesh Verma arrived on site. Met with Amitabh Sen of Indore Trans-Logistics in the supervisor cabin. Meeting lasted 45 minutes. Warehouse supervisor Vikas Jain was observed providing ledger sheets to both subjects.
[2026-06-10 14:50] Subjects departed in separate directions.

[2026-06-12 10:55] Surveillance observed incoming vehicle MP-09-GF-8801 entering Vijay Nagar Warehouse.
[2026-06-12 11:00] Rajesh Verma exited vehicle MP-09-GF-8801 and entered the facility office. Observed engaging in rapid documentation review and digital banking activity via mobile terminal.
[2026-06-12 12:15] Subject departed towards AB Road.
""",
    },
    {
        "evidence_id": "EVD-001-VEH01",
        "filename": "Logistics-Dispatch-Log.csv",
        "document_type": "CSV",
        "mime_type": "text/csv",
        "document_language": "en",
        "notes": "Fleet dispatch and telematics registry tracking commercial freight carrier vehicles.",
        "content": """timestamp,vehicle_no,driver,origin,destination,dispatch_order,status
2026-06-05T08:30:00,MP-09-AB-4412,Sunil Deshmukh,Pithampur Industrial Hub,Dewas Naka Depot,DO-1042,Completed
2026-06-09T09:15:00,MP-09-AB-4412,Sunil Deshmukh,Pithampur Industrial Hub,Indore Main Hub,DO-1088,Completed
2026-06-12T10:45:00,MP-09-GF-8801,Rajesh Verma,Malwa Freight Office,Vijay Nagar Warehouse,DO-1115,Completed
2026-06-17T07:45:00,MP-09-AB-4412,Sunil Deshmukh,Pithampur Industrial Hub,Dewas Naka Depot,DO-1150,Completed
2026-06-24T04:15:00,MP-09-AB-4412,Sunil Deshmukh,Pithampur Industrial Hub,Dewas Naka Depot,DO-1204,Unscheduled Night Transit
""",
    },
]


def run():
    db = SessionLocal()
    try:
        # ==========================================
        # 1. Users
        # ==========================================
        users_map = {}
        for uid_code, name, role in [
            ("INV-017", "Inspector Rahul Mehta", "LEAD_INVESTIGATOR"),
            ("INV-021", "SI Ananya Sharma", "INVESTIGATOR"),
            ("INV-032", "SI Vikram Patel", "INVESTIGATOR"),
        ]:
            user = db.scalar(select(User).where(User.investigator_id == uid_code))
            if not user:
                user = User(
                    investigator_id=uid_code,
                    name=name,
                    password_hash="prototype-configured",
                    role=role,
                )
                db.add(user)
                db.flush()
            users_map[uid_code] = user

        rahul = users_map["INV-017"]
        ananya = users_map["INV-021"]
        vikram = users_map["INV-032"]

        # ==========================================
        # 2. CASE-001 (Indore Transport Network)
        # ==========================================
        case1 = db.scalar(select(Case).where(Case.case_number == "CASE-001"))
        if not case1:
            case1 = Case(
                case_number="CASE-001",
                title="Indore Transport Network",
                status="ACTIVE",
                priority="MEDIUM",
                summary="Ongoing investigation into unauthorized consignment routing, off-manifest cargo diversions, and correlated financial disbursements across the Indore–Pithampur–Dewas logistics corridor operated by Malwa Freight Carriers and Indore Trans-Logistics.",
                lead_investigator_id=ananya.id,
            )
            db.add(case1)
            db.flush()

            db.add(CaseAssignment(case_id=case1.id, user_id=ananya.id, assignment_role="LEAD"))
            db.add(CaseAssignment(case_id=case1.id, user_id=rahul.id, assignment_role="SUPERVISOR"))
            db.add(CaseAssignment(case_id=case1.id, user_id=vikram.id, assignment_role="INVESTIGATOR"))
            db.flush()

            db.add(
                AuditEvent(
                    actor_id=ananya.id,
                    action="CASE_CREATED",
                    resource_type="CASE",
                    resource_id=case1.case_number,
                    case_id=case1.id,
                    result="SUCCESS",
                    metadata_json={"title": case1.title, "priority": case1.priority},
                )
            )

        # Seed CASE-001 entities and evidence
        entities_data_001 = [
            ("PERSON", "Rajesh Verma", "rajesh_verma", {"role": "Logistics Operations Manager", "organization": "Malwa Freight Carriers"}),
            ("PERSON", "Sunil Deshmukh", "sunil_deshmukh", {"role": "Fleet Coordinator / Driver", "organization": "Malwa Freight Carriers"}),
            ("PERSON", "Amitabh Sen", "amitabh_sen", {"role": "Consignor / Cargo Broker", "organization": "Indore Trans-Logistics"}),
            ("PERSON", "Pooja Kulkarni", "pooja_kulkarni", {"role": "Head of Accounts", "organization": "Malwa Freight Carriers"}),
            ("PERSON", "Vikas Jain", "vikas_jain", {"role": "Warehouse Supervisor", "organization": "Vijay Nagar Depot"}),
            ("ORGANIZATION", "Malwa Freight Carriers", "malwa_freight_carriers", {"sector": "Logistics & Freight Transport", "jurisdiction": "Indore Region"}),
            ("ORGANIZATION", "Indore Trans-Logistics", "indore_trans_logistics", {"sector": "Cargo Brokerage & Forwarding", "jurisdiction": "Madhya Pradesh"}),
            ("PHONE", "+91-98260-11223", "+91-98260-11223", {"primary_user": "Rajesh Verma", "carrier": "Airtel MP"}),
            ("PHONE", "+91-94250-99881", "+91-94250-99881", {"primary_user": "Amitabh Sen", "carrier": "Jio MP"}),
            ("VEHICLE", "MP-09-AB-4412", "mp_09_ab_4412", {"type": "Heavy Commercial Transport", "registered_owner": "Malwa Freight Carriers"}),
            ("VEHICLE", "MP-09-GF-8801", "mp_09_gf_8801", {"type": "Light Commercial Utility Van", "registered_owner": "Rajesh Verma"}),
            ("LOCATION", "Vijay Nagar Warehouse, Indore", "vijay_nagar_warehouse_indore", {"address": "Plot 44-B, Vijay Nagar Industrial Area, Indore"}),
            ("LOCATION", "Dewas Naka Depot", "dewas_naka_depot", {"address": "Dewas Naka Transport Nagar, Indore"}),
            ("LOCATION", "Pithampur Industrial Hub", "pithampur_industrial_hub", {"address": "Sector 3 Industrial Corridor, Pithampur"}),
        ]

        entities_001 = {}
        for etype, cname, ikey, meta in entities_data_001:
            ent = db.scalar(select(Entity).where(Entity.case_id == case1.id, Entity.canonical_name == cname))
            if not ent:
                ent = Entity(
                    case_id=case1.id,
                    entity_type=etype,
                    canonical_name=cname,
                    metadata_json={"identity_key": ikey, **meta},
                )
                db.add(ent)
                db.flush()
            entities_001[cname] = ent

        evidence_records_001 = {}
        for item in EVIDENCE_DATA_CASE_001:
            eid = item["evidence_id"]
            filename = item["filename"]
            folder = STORAGE_ROOT / eid
            folder.mkdir(parents=True, exist_ok=True)
            filepath = folder / filename
            filepath.write_text(item["content"], encoding="utf-8")

            file_bytes = filepath.read_bytes()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            file_size = len(file_bytes)
            storage_key = f"{eid}/{filename}"

            evd = db.scalar(select(Evidence).where(Evidence.evidence_id == eid))
            if not evd:
                evd = Evidence(
                    evidence_id=eid,
                    case_id=case1.id,
                    filename=filename,
                    document_type=item["document_type"],
                    mime_type=item["mime_type"],
                    storage_key=storage_key,
                    document_language=item["document_language"],
                    uploaded_by_id=ananya.id,
                    processing_status="EXTRACTION_COMPLETED",
                    ocr_status="COMPLETED",
                    extraction_status="COMPLETED",
                    integrity_status="VERIFIED",
                    ocr_text=item["content"],
                    ocr_pages=[item["content"]],
                    notes=item["notes"],
                    processed_at=now(),
                    ingestion_method="structured" if item["document_type"] == "CSV" else "document",
                )
                db.add(evd)
                db.flush()

                integrity = EvidenceIntegrity(
                    evidence_id=evd.id,
                    sha256=sha256_hash,
                    file_size=file_size,
                    algorithm="SHA-256",
                    ledger_record_id=f"LEDGER-{eid}-{uid()[:8].upper()}",
                    registration_status="REGISTERED",
                    verification_status="VERIFIED",
                    verified_at=now(),
                )
                db.add(integrity)
                db.flush()
            evidence_records_001[eid] = evd

        # Mentions CASE-001
        mentions_data_001 = [
            ("EVD-001-FIR01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 480, 492, 0.98),
            ("EVD-001-FIR01", "Sunil Deshmukh", "PERSON", "Sunil Deshmukh", "Sunil Deshmukh", 516, 530, 0.98),
            ("EVD-001-FIR01", "Malwa Freight Carriers", "ORGANIZATION", "Malwa Freight Carriers", "Malwa Freight Carriers", 250, 272, 0.99),
            ("EVD-001-FIR01", "Dewas Naka Depot", "LOCATION", "Dewas Naka Depot", "Dewas Naka Depot", 380, 396, 0.97),
            ("EVD-001-FIR01", "Pithampur Industrial Hub", "LOCATION", "Pithampur Industrial Hub", "Pithampur Industrial Hub", 210, 234, 0.97),
            ("EVD-001-FIR01", "MP-09-AB-4412", "VEHICLE", "MP-09-AB-4412", "MP-09-AB-4412", 610, 623, 0.99),
            ("EVD-001-CDR01", "+91-98260-11223", "PHONE", "+91-98260-11223", "+91-98260-11223", 25, 40, 0.99),
            ("EVD-001-CDR01", "+91-94250-99881", "PHONE", "+91-94250-99881", "+91-94250-99881", 41, 56, 0.99),
            ("EVD-001-FIN01", "Malwa Freight Carriers", "ORGANIZATION", "Malwa Freight Carriers (A/C)", "Malwa Freight Carriers", 25, 37, 0.99),
            ("EVD-001-FIN01", "Pooja Kulkarni", "PERSON", "Pooja Kulkarni (Authorizer)", "Pooja Kulkarni", 0, 0, 0.96),
            ("EVD-001-FIN01", "Amitabh Sen", "PERSON", "Amitabh Sen (Beneficiary)", "Amitabh Sen", 260, 271, 0.98),
            ("EVD-001-SURV01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 220, 232, 0.98),
            ("EVD-001-SURV01", "Amitabh Sen", "PERSON", "Amitabh Sen", "Amitabh Sen", 245, 256, 0.98),
            ("EVD-001-SURV01", "Vikas Jain", "PERSON", "Vikas Jain", "Vikas Jain", 340, 350, 0.96),
            ("EVD-001-SURV01", "Vijay Nagar Warehouse, Indore", "LOCATION", "Vijay Nagar Warehouse, Indore", "Vijay Nagar Warehouse, Indore", 30, 59, 0.98),
            ("EVD-001-SURV01", "MP-09-GF-8801", "VEHICLE", "MP-09-GF-8801", "MP-09-GF-8801", 450, 463, 0.99),
            ("EVD-001-VEH01", "MP-09-AB-4412", "VEHICLE", "MP-09-AB-4412", "MP-09-AB-4412", 20, 33, 0.99),
            ("EVD-001-VEH01", "MP-09-GF-8801", "VEHICLE", "MP-09-GF-8801", "MP-09-GF-8801", 160, 173, 0.99),
            ("EVD-001-VEH01", "Sunil Deshmukh", "PERSON", "Sunil Deshmukh", "Sunil Deshmukh", 34, 48, 0.98),
            ("EVD-001-VEH01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 174, 186, 0.98),
        ]

        mentions_001 = {}
        for eid, ent_name, mtype, text, norm_val, start, end, conf in mentions_data_001:
            evd = evidence_records_001[eid]
            ent = entities_001[ent_name]
            mkey = f"{eid}:{mtype}:{start}:{end}:{norm_val}"
            rec = db.scalar(select(EntityMentionRecord).where(EntityMentionRecord.evidence_id == evd.id, EntityMentionRecord.mention_key == mkey))
            if not rec:
                rec = EntityMentionRecord(
                    evidence_id=evd.id,
                    entity_id=ent.id,
                    mention_key=mkey,
                    entity_type=mtype,
                    text=text,
                    normalized_value=norm_val,
                    start=start,
                    end=end,
                    confidence=conf,
                    resolution_status="CONFIRMED",
                    resolution_confidence=conf,
                )
                db.add(rec)
                db.flush()
            mentions_001[f"{eid}:{ent_name}"] = rec

        # ==========================================
        # 3. CASE-003 (Restricted Inquiry Shell)
        # ==========================================
        case3 = db.scalar(select(Case).where(Case.case_number == "CASE-003"))
        if not case3:
            case3 = Case(
                case_number="CASE-003",
                title="Restricted Financial Network Investigation",
                status="ACTIVE",
                priority="HIGH",
                summary="A restricted inquiry conducted by the Economic Offences Wing into offshore financial layering and corporate banking channels associated with intermediate account ACC-LOGI-17. Access is strictly restricted to assigned authorized personnel.",
                lead_investigator_id=ananya.id,
            )
            db.add(case3)
            db.flush()

            # Only Ananya is assigned; Rahul (INV-017) does not have access initially
            db.add(CaseAssignment(case_id=case3.id, user_id=ananya.id, assignment_role="LEAD"))
            db.flush()

            db.add(
                AuditEvent(
                    actor_id=ananya.id,
                    action="CASE_CREATED",
                    resource_type="CASE",
                    resource_id=case3.case_number,
                    case_id=case3.id,
                    result="SUCCESS",
                    metadata_json={"title": case3.title, "priority": case3.priority},
                )
            )

        # ==========================================
        # 4. CASE-002 (Mumbai Warehouse Network Investigation)
        # ==========================================
        case2 = db.scalar(select(Case).where(Case.case_number == "CASE-002"))
        if not case2:
            case2 = Case(
                case_number="CASE-002",
                title="Mumbai Warehouse Network Investigation",
                status="ACTIVE",
                priority="HIGH",
                summary="Investigation initiated following FIR-183/2026 concerning an unauthorized consignment diversion at Warehouse 14 in MIDC Industrial Estate, Andheri East, Mumbai. Combining unstructured FIR and surveillance logs with structured CDR telecommunications, banking ledger transactions, and vehicle transit movements to establish entities, relationships, events, and suspicious patterns.",
                lead_investigator_id=rahul.id,
            )
            db.add(case2)
            db.flush()

            db.add(CaseAssignment(case_id=case2.id, user_id=rahul.id, assignment_role="LEAD"))
            db.add(CaseAssignment(case_id=case2.id, user_id=vikram.id, assignment_role="INVESTIGATOR"))
            db.flush()

            db.add(
                AuditEvent(
                    actor_id=rahul.id,
                    action="CASE_CREATED",
                    resource_type="CASE",
                    resource_id=case2.case_number,
                    case_id=case2.id,
                    result="SUCCESS",
                    metadata_json={"title": case2.title, "priority": case2.priority},
                )
            )

        # Preload CASE-002 Evidence, Entities, Mentions, Resolutions, Relations, and Events
        # Clean existing CASE-002 evidence if any exists to ensure consistent state
        old_case2_evs = db.scalars(select(Evidence).where(Evidence.case_id == case2.id)).all()
        for old_ev in old_case2_evs:
            db.delete(old_ev)
        db.flush()

        # 4.1 Canonical Entities for CASE-002 (~15 Entities)
        entities_data_002 = [
            # PEOPLE
            ("PERSON", "Rohan Mehta", "rohan_mehta", {"role": "Operations Manager", "organization": "Apex Logistics Mumbai"}),
            ("PERSON", "Rajesh Verma", "rajesh_verma", {"role": "Logistics & Fleet Coordinator", "organization": "Apex Logistics Mumbai"}),
            ("PERSON", "Sunil Deshmukh", "sunil_deshmukh", {"role": "Commercial Transport Driver", "organization": "Apex Logistics Mumbai"}),
            ("PERSON", "Arjun Deshmukh", "arjun_deshmukh", {"role": "Warehouse Supervisor", "organization": "Warehouse 14"}),
            # ORGANIZATIONS
            ("ORGANIZATION", "Apex Logistics Mumbai", "apex_logistics_mumbai", {"sector": "Commercial Freight Forwarding", "jurisdiction": "Mumbai Suburban"}),
            # PHONES
            ("PHONE", "+91 90000 32741", "+91 90000 32741", {"primary_user": "Rohan Mehta", "carrier": "Airtel Mumbai"}),
            ("PHONE", "+91 90000 58126", "+91 90000 58126", {"primary_user": "Rajesh Verma", "carrier": "Jio Mumbai"}),
            ("PHONE", "+91 90000 61483", "+91 90000 61483", {"primary_user": "Apex Logistics Dispatch Line", "carrier": "Vodafone Idea"}),
            # VEHICLES
            ("VEHICLE", "MH-04-KT-2187", "mh_04_kt_2187", {"type": "Commercial Freight Carrier", "registered_owner": "Apex Logistics Mumbai"}),
            # LOCATIONS
            ("LOCATION", "Warehouse 14", "warehouse_14", {"address": "Plot 14, MIDC Industrial Estate, Andheri East, Mumbai"}),
            ("LOCATION", "MIDC Industrial Estate", "midc_industrial_estate", {"address": "MIDC Zone, Andheri East, Mumbai"}),
            ("LOCATION", "Andheri East", "andheri_east", {"address": "Andheri East Logistics Hub, Mumbai"}),
            # ACCOUNTS
            ("ACCOUNT", "ACC-ROHAN-01", "acc_rohan_01", {"account_holder": "Rohan Mehta", "bank": "Mumbai Commercial Bank"}),
            ("ACCOUNT", "ACC-LOGI-17", "acc_logi_17", {"account_holder": "Apex Logistics Corporate", "bank": "Metro Treasury Bank"}),
            ("ACCOUNT", "ACC-SUPPLY-04", "acc_supply_04", {"account_holder": "Warehouse Supplies & Fleet", "bank": "National Clearing"}),
        ]

        entities_002 = {}
        for etype, cname, ikey, meta in entities_data_002:
            ent = db.scalar(select(Entity).where(Entity.case_id == case2.id, Entity.canonical_name == cname))
            if not ent:
                ent = Entity(
                    case_id=case2.id,
                    entity_type=etype,
                    canonical_name=cname,
                    metadata_json={"identity_key": ikey, **meta},
                )
                db.add(ent)
                db.flush()
            entities_002[cname] = ent

        # 4.2 Evidence Records for CASE-002 (6 Files)
        case_002_evidence_manifest = [
            {
                "evidence_id": "EVD-002-FIR01",
                "filename": "FIR-183-2026.pdf",
                "document_type": "PDF",
                "mime_type": "application/pdf",
                "ingestion_method": "document",
                "notes": "First Information Report registered at MIDC Police Station regarding unauthorized goods removal from Warehouse 14.",
                "ocr_text": """FIRST INFORMATION REPORT (FIR NO. 183/2026)
MIDC Police Station, Andheri East, Mumbai | Case Reference: CASE-002

FIR Number: FIR-183-2026
Police Station: MIDC Police Station
Registration Date: 24 August 2026
Incident Date & Time: 23 August 2026 at 22:40
Complainant Name: Arjun Deshmukh
Place of Occurrence: Warehouse 14, MIDC Industrial Estate, Andheri East
Complainant Phone: +91 90000 18427
Applicable Law: IPC Sections 457, 380, 34

STATEMENT OF THE COMPLAINANT:
I, Arjun Deshmukh, employed as warehouse supervisor at Warehouse 14, MIDC Industrial Estate, Andheri East, report that on 23 August 2026 at approximately 22:40 hrs, an unauthorized consignment diversion occurred. High-value freight consignments registered under Apex Logistics Mumbai were unlawfully moved out of the warehouse premises.

Security records log that suspect Rohan Mehta (contact: +91 90000 32741) and fleet coordinator Rajesh Verma coordinated the movement of commercial carrier vehicle MH-04-KT-2187 near the rear loading bay. The vehicle entered Warehouse 14 during evening hours and departed without standard gate clearance.

DOCUMENTED CLUES & PERSONS OF INTEREST:
- Primary Subject: Rohan Mehta (Operations Manager, Phone: +91 90000 32741)
- Logistics Associate: Rajesh Verma (Fleet Coordinator, Apex Logistics Mumbai)
- Identified Vehicle: MH-04-KT-2187 (Commercial carrier observed at Warehouse 14)
- Incident Location: Warehouse 14 (MIDC Industrial Estate, Andheri East)
""",
                "structured_json": None,
            },
            {
                "evidence_id": "EVD-002-CDR01",
                "filename": "CDR-August-2026.csv",
                "document_type": "CSV",
                "mime_type": "text/csv",
                "ingestion_method": "structured",
                "notes": "Telecommunication CDR logs reflecting baseline communications vs sharp activity spike on 21 August 2026.",
                "ocr_text": """timestamp,caller,receiver,duration_seconds,cell_tower
2026-08-08T09:14:00,+91 90000 32741,+91 90000 58126,68,MIDC Industrial Estate
2026-08-10T18:42:00,+91 90000 58126,+91 90000 32741,91,Andheri East
2026-08-14T11:07:00,+91 90000 32741,+91 90000 58126,45,MIDC Industrial Estate
2026-08-18T17:20:00,+91 90000 58126,+91 90000 32741,78,Andheri East
2026-08-21T09:15:00,+91 90000 32741,+91 90000 58126,240,Andheri East
2026-08-21T10:45:00,+91 90000 32741,+91 90000 58126,185,MIDC Industrial Estate
2026-08-21T12:30:00,+91 90000 58126,+91 90000 32741,310,MIDC Industrial Estate
2026-08-21T14:10:00,+91 90000 32741,+91 90000 61483,195,Andheri East
2026-08-21T16:25:00,+91 90000 61483,+91 90000 32741,280,Andheri East
2026-08-21T18:40:00,+91 90000 32741,+91 90000 58126,420,MIDC Industrial Estate
2026-08-21T21:15:00,+91 90000 58126,+91 90000 32741,350,MIDC Industrial Estate
2026-08-21T23:40:00,+91 90000 32741,+91 90000 61483,290,Andheri East
2026-08-22T08:30:00,+91 90000 32741,+91 90000 58126,160,MIDC Industrial Estate
2026-08-22T15:20:00,+91 90000 32741,+91 90000 61483,145,Andheri East
2026-08-23T11:15:00,+91 90000 32741,+91 90000 58126,190,Andheri East
2026-08-23T20:15:00,+91 90000 32741,+91 90000 58126,260,MIDC Industrial Estate
2026-08-23T21:05:00,+91 90000 32741,+91 90000 61483,180,MIDC Industrial Estate
2026-08-23T22:45:00,+91 90000 58126,+91 90000 32741,340,MIDC Industrial Estate
""",
                "structured_json": {
                    "method": "Structured Parsing",
                    "columns": ["timestamp", "caller", "receiver", "duration_seconds", "cell_tower"],
                    "rowCount": 18,
                    "summary": "Telecommunication Call Detail Records showing baseline contacts and a notable 8-call spike on 21 August 2026.",
                    "records": [
                        {"timestamp": "2026-08-08T09:14:00", "caller": "+91 90000 32741", "receiver": "+91 90000 58126", "duration_seconds": "68", "cell_tower": "MIDC Industrial Estate"},
                        {"timestamp": "2026-08-10T18:42:00", "caller": "+91 90000 58126", "receiver": "+91 90000 32741", "duration_seconds": "91", "cell_tower": "Andheri East"},
                        {"timestamp": "2026-08-14T11:07:00", "caller": "+91 90000 32741", "receiver": "+91 90000 58126", "duration_seconds": "45", "cell_tower": "MIDC Industrial Estate"},
                        {"timestamp": "2026-08-18T17:20:00", "caller": "+91 90000 58126", "receiver": "+91 90000 32741", "duration_seconds": "78", "cell_tower": "Andheri East"},
                        {"timestamp": "2026-08-21T09:15:00", "caller": "+91 90000 32741", "receiver": "+91 90000 58126", "duration_seconds": "240", "cell_tower": "Andheri East"},
                        {"timestamp": "2026-08-21T10:45:00", "caller": "+91 90000 32741", "receiver": "+91 90000 58126", "duration_seconds": "185", "cell_tower": "MIDC Industrial Estate"},
                        {"timestamp": "2026-08-21T12:30:00", "caller": "+91 90000 58126", "receiver": "+91 90000 32741", "duration_seconds": "310", "cell_tower": "MIDC Industrial Estate"},
                        {"timestamp": "2026-08-21T14:10:00", "caller": "+91 90000 32741", "receiver": "+91 90000 61483", "duration_seconds": "195", "cell_tower": "Andheri East"},
                        {"timestamp": "2026-08-21T16:25:00", "caller": "+91 90000 61483", "receiver": "+91 90000 32741", "duration_seconds": "280", "cell_tower": "Andheri East"},
                        {"timestamp": "2026-08-21T18:40:00", "caller": "+91 90000 32741", "receiver": "+91 90000 58126", "duration_seconds": "420", "cell_tower": "MIDC Industrial Estate"},
                        {"timestamp": "2026-08-21T21:15:00", "caller": "+91 90000 58126", "receiver": "+91 90000 32741", "duration_seconds": "350", "cell_tower": "MIDC Industrial Estate"},
                        {"timestamp": "2026-08-21T23:40:00", "caller": "+91 90000 32741", "receiver": "+91 90000 61483", "duration_seconds": "290", "cell_tower": "Andheri East"},
                    ]
                }
            },
            {
                "evidence_id": "EVD-002-FIN01",
                "filename": "Financial-Transactions-August-2026.csv",
                "document_type": "CSV",
                "mime_type": "text/csv",
                "ingestion_method": "structured",
                "notes": "Corporate bank transaction records showing routine maintenance payments and an anomalous disbursement of ₹4,80,000 on 23 August 2026.",
                "ocr_text": """timestamp,sender_account,receiver_account,amount,description
2026-08-10T12:18:00,ACC-ROHAN-01,ACC-LOGI-17,42000,Fleet maintenance advance
2026-08-14T15:42:00,ACC-LOGI-17,ACC-SUPPLY-04,38500,Warehouse supply settlement
2026-08-18T11:20:00,ACC-ROHAN-01,ACC-LOGI-17,45000,Freight handling disbursement
2026-08-23T11:30:00,ACC-ROHAN-01,ACC-LOGI-17,480000,Urgent consignment handling advance (Anomalous)
2026-08-23T14:45:00,ACC-LOGI-17,ACC-SUPPLY-04,35000,Special transit fuel advance
""",
                "structured_json": {
                    "method": "Structured Parsing",
                    "columns": ["timestamp", "sender_account", "receiver_account", "amount", "description"],
                    "rowCount": 5,
                    "summary": "Corporate banking transaction ledger showing baseline operational transfers (₹35,000-₹45,000) and an anomalous spike to ₹4,80,000 on 23 August 2026.",
                    "records": [
                        {"timestamp": "2026-08-10T12:18:00", "sender_account": "ACC-ROHAN-01", "receiver_account": "ACC-LOGI-17", "amount": "42000", "description": "Fleet maintenance advance"},
                        {"timestamp": "2026-08-14T15:42:00", "sender_account": "ACC-LOGI-17", "receiver_account": "ACC-SUPPLY-04", "amount": "38500", "description": "Warehouse supply settlement"},
                        {"timestamp": "2026-08-18T11:20:00", "sender_account": "ACC-ROHAN-01", "receiver_account": "ACC-LOGI-17", "amount": "45000", "description": "Freight handling disbursement"},
                        {"timestamp": "2026-08-23T11:30:00", "sender_account": "ACC-ROHAN-01", "receiver_account": "ACC-LOGI-17", "amount": "480000", "description": "Urgent consignment handling advance (Anomalous)"},
                        {"timestamp": "2026-08-23T14:45:00", "sender_account": "ACC-LOGI-17", "receiver_account": "ACC-SUPPLY-04", "amount": "35000", "description": "Special transit fuel advance"},
                    ]
                }
            },
            {
                "evidence_id": "EVD-002-SURV01",
                "filename": "Surveillance-Report-01.pdf",
                "document_type": "PDF",
                "mime_type": "application/pdf",
                "ingestion_method": "document",
                "notes": "Field surveillance observation log from Crime Branch team monitoring Warehouse 14 on 23 August 2026.",
                "ocr_text": """SURVEILLANCE OBSERVATION LOG
Crime Branch Special Operations Squad | Case Reference: CASE-002

Date of Observation: 23 August 2026
Target Location: Warehouse 14, MIDC Industrial Estate, Andheri East
Observation Window: 20:55 hrs to 22:50 hrs
Observed Vehicle: White commercial carrier MH-04-KT-2187

FIELD OBSERVATIONS:
On 23 August 2026 at 20:55 hrs, surveillance officers took position near the rear access point of Warehouse 14 in MIDC Industrial Estate, Andheri East.

At 21:08 hrs, commercial vehicle MH-04-KT-2187 entered Warehouse 14 through the service road. Subject Rohan Mehta arrived on site at 21:34 hrs and entered the warehouse office. At 21:51 hrs, Rohan Mehta met with Rajesh Verma and driver Sunil Deshmukh. The subjects supervised the loading of crates into vehicle MH-04-KT-2187.

At 22:40 hrs, loading was completed. At 22:47 hrs, vehicle MH-04-KT-2187 departed Warehouse 14 towards Andheri East.
""",
                "structured_json": None,
            },
            {
                "evidence_id": "EVD-002-INTEL01",
                "filename": "Field-Intelligence-Report.pdf",
                "document_type": "PDF",
                "mime_type": "application/pdf",
                "ingestion_method": "document",
                "notes": "Special Intelligence Wing memo on Apex Logistics Mumbai and cross-case financial link to CASE-003.",
                "ocr_text": """FIELD INTELLIGENCE NOTE
Special Intelligence Wing, Mumbai Suburban | Case Reference: CASE-002

Date of Report: 22 August 2026
Target Organization: Apex Logistics Mumbai
Primary Subject: Rohan Mehta
Target Facility: Warehouse 14, MIDC Industrial Estate, Andheri East

INVESTIGATIVE LEADS:
Field intelligence indicates that operations manager Rohan Mehta has coordinated unauthorized freight diversions for Apex Logistics Mumbai using storage space at Warehouse 14 in MIDC Industrial Estate, Andheri East.

Technical subscriber analysis shows extensive telecommunication contact between Rohan Mehta (+91 90000 32741), fleet coordinator Rajesh Verma (+91 90000 58126), and field contact +91 90000 61483. A sharp communication spike occurred on 21 August 2026.

CROSS-CASE LINKAGE: Corporate account ACC-LOGI-17 used by Apex Logistics Mumbai shares financial links with an offshore inquiry monitored by the Economic Offences Wing in CASE-003. Investigator INV-017 should submit an access request to CASE-003.
""",
                "structured_json": None,
            },
            {
                "evidence_id": "EVD-002-VEH01",
                "filename": "Vehicle-Movement-Records.csv",
                "document_type": "CSV",
                "mime_type": "text/csv",
                "ingestion_method": "structured",
                "notes": "Fleet telematics and toll log tracking commercial vehicle MH-04-KT-2187 movements.",
                "ocr_text": """timestamp,vehicle_number,location,driver
2026-08-20T08:42:00,MH-04-KT-2187,Warehouse 14,Sunil Deshmukh
2026-08-20T17:30:00,MH-04-KT-2187,MIDC Industrial Estate,Sunil Deshmukh
2026-08-22T14:15:00,MH-04-KT-2187,Andheri East,Rajesh Verma
2026-08-23T21:05:00,MH-04-KT-2187,Warehouse 14,Rajesh Verma
2026-08-23T22:48:00,MH-04-KT-2187,Andheri East,Rajesh Verma
""",
                "structured_json": {
                    "method": "Structured Parsing",
                    "columns": ["timestamp", "vehicle_number", "location", "driver"],
                    "rowCount": 5,
                    "summary": "Vehicle telemetry and checkpoint log capturing movement of carrier MH-04-KT-2187 between Andheri East and Warehouse 14.",
                    "records": [
                        {"timestamp": "2026-08-20T08:42:00", "vehicle_number": "MH-04-KT-2187", "location": "Warehouse 14", "driver": "Sunil Deshmukh"},
                        {"timestamp": "2026-08-20T17:30:00", "vehicle_number": "MH-04-KT-2187", "location": "MIDC Industrial Estate", "driver": "Sunil Deshmukh"},
                        {"timestamp": "2026-08-22T14:15:00", "vehicle_number": "MH-04-KT-2187", "location": "Andheri East", "driver": "Rajesh Verma"},
                        {"timestamp": "2026-08-23T21:05:00", "vehicle_number": "MH-04-KT-2187", "location": "Warehouse 14", "driver": "Rajesh Verma"},
                        {"timestamp": "2026-08-23T22:48:00", "vehicle_number": "MH-04-KT-2187", "location": "Andheri East", "driver": "Rajesh Verma"},
                    ]
                }
            },
        ]

        evidence_records_002 = {}
        for item in case_002_evidence_manifest:
            eid = item["evidence_id"]
            filename = item["filename"]
            folder = STORAGE_ROOT / eid
            folder.mkdir(parents=True, exist_ok=True)
            filepath = folder / filename

            # Copy from seed directory if exists, else write text
            src_file = CASE_002_SRC / filename
            if src_file.exists():
                shutil.copy2(src_file, filepath)
            else:
                filepath.write_text(item["ocr_text"], encoding="utf-8")

            file_bytes = filepath.read_bytes()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            file_size = len(file_bytes)
            storage_key = f"{eid}/{filename}"

            extraction_payload = {
                "text": item["ocr_text"],
                "pages": [item["ocr_text"]],
                "language": {"code": "en", "confidence": 0.99},
                "ingestion_method": item["ingestion_method"],
                "structured": item["structured_json"],
            }

            evd = Evidence(
                evidence_id=eid,
                case_id=case2.id,
                filename=filename,
                document_type=item["document_type"],
                mime_type=item["mime_type"],
                storage_key=storage_key,
                document_language="en",
                uploaded_by_id=rahul.id,
                processing_status="EXTRACTION_COMPLETED",
                ocr_status="COMPLETED",
                extraction_status="COMPLETED",
                integrity_status="VERIFIED",
                ocr_text=item["ocr_text"],
                ocr_pages=[item["ocr_text"]],
                notes=item["notes"],
                processed_at=now(),
                ingestion_method=item["ingestion_method"],
                structured_json=item["structured_json"],
                extraction_json=extraction_payload,
            )
            db.add(evd)
            db.flush()

            integrity = EvidenceIntegrity(
                evidence_id=evd.id,
                sha256=sha256_hash,
                file_size=file_size,
                algorithm="SHA-256",
                ledger_record_id=f"LEDGER-{eid}-{uid()[:8].upper()}",
                registration_status="REGISTERED",
                verification_status="VERIFIED",
                verified_at=now(),
            )
            db.add(integrity)
            db.flush()

            db.add(
                AuditEvent(
                    actor_id=rahul.id,
                    action="EVIDENCE_UPLOADED",
                    resource_type="EVIDENCE",
                    resource_id=eid,
                    case_id=case2.id,
                    result="SUCCESS",
                    metadata_json={"filename": filename, "type": item["document_type"]},
                )
            )
            db.add(
                AuditEvent(
                    actor_id=rahul.id,
                    action="EVIDENCE_HASH_REGISTERED",
                    resource_type="EVIDENCE",
                    resource_id=eid,
                    case_id=case2.id,
                    result="SUCCESS",
                    metadata_json={"sha256": sha256_hash, "ledger_record_id": integrity.ledger_record_id},
                )
            )
            evidence_records_002[eid] = evd

        # 4.3 Mentions for CASE-002 (including 3 ambiguous mentions for Human Review)
        mentions_data_002 = [
            # In EVD-002-FIR01
            ("EVD-002-FIR01", "Rohan Mehta", "PERSON", "Rohan Mehta", "Rohan Mehta", 480, 491, 0.98, "CONFIRMED"),
            ("EVD-002-FIR01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 518, 530, 0.98, "CONFIRMED"),
            ("EVD-002-FIR01", "Arjun Deshmukh", "PERSON", "Arjun Deshmukh", "Arjun Deshmukh", 180, 194, 0.98, "CONFIRMED"),
            ("EVD-002-FIR01", "Apex Logistics Mumbai", "ORGANIZATION", "Apex Logistics Mumbai", "Apex Logistics Mumbai", 340, 361, 0.99, "CONFIRMED"),
            ("EVD-002-FIR01", "+91 90000 32741", "PHONE", "+91 90000 32741", "+91 90000 32741", 500, 515, 0.99, "CONFIRMED"),
            ("EVD-002-FIR01", "MH-04-KT-2187", "VEHICLE", "MH-04-KT-2187", "MH-04-KT-2187", 580, 593, 0.99, "CONFIRMED"),
            ("EVD-002-FIR01", "Warehouse 14", "LOCATION", "Warehouse 14", "Warehouse 14", 230, 242, 0.98, "CONFIRMED"),
            ("EVD-002-FIR01", "MIDC Industrial Estate", "LOCATION", "MIDC Industrial Estate", "MIDC Industrial Estate", 244, 266, 0.98, "CONFIRMED"),
            ("EVD-002-FIR01", "Andheri East", "LOCATION", "Andheri East", "Andheri East", 268, 280, 0.98, "CONFIRMED"),

            # In EVD-002-CDR01
            ("EVD-002-CDR01", "+91 90000 32741", "PHONE", "+91 90000 32741", "+91 90000 32741", 20, 35, 0.99, "CONFIRMED"),
            ("EVD-002-CDR01", "+91 90000 58126", "PHONE", "+91 90000 58126", "+91 90000 58126", 36, 51, 0.99, "CONFIRMED"),
            ("EVD-002-CDR01", "+91 90000 61483", "PHONE", "+91 90000 61483", "+91 90000 61483", 52, 67, 0.99, "CONFIRMED"),
            ("EVD-002-CDR01", "Rohan Mehta", "PERSON", "Rohan Mehta (Subscriber)", "Rohan Mehta", 0, 0, 0.95, "CONFIRMED"),
            ("EVD-002-CDR01", "Rajesh Verma", "PERSON", "Rajesh Verma (Subscriber)", "Rajesh Verma", 0, 0, 0.95, "CONFIRMED"),
            ("EVD-002-CDR01", "Apex Logistics Mumbai", "ORGANIZATION", "Apex Logistics Mumbai (Subscriber)", "Apex Logistics Mumbai", 0, 0, 0.95, "CONFIRMED"),

            # In EVD-002-FIN01
            ("EVD-002-FIN01", "ACC-ROHAN-01", "ACCOUNT", "ACC-ROHAN-01", "ACC-ROHAN-01", 20, 32, 0.99, "CONFIRMED"),
            ("EVD-002-FIN01", "ACC-LOGI-17", "ACCOUNT", "ACC-LOGI-17", "ACC-LOGI-17", 33, 44, 0.99, "CONFIRMED"),
            ("EVD-002-FIN01", "ACC-SUPPLY-04", "ACCOUNT", "ACC-SUPPLY-04", "ACC-SUPPLY-04", 45, 58, 0.99, "CONFIRMED"),
            ("EVD-002-FIN01", "Rohan Mehta", "PERSON", "Rohan Mehta (Remitter)", "Rohan Mehta", 0, 0, 0.96, "CONFIRMED"),

            # In EVD-002-SURV01
            ("EVD-002-SURV01", "Rohan Mehta", "PERSON", "Rohan Mehta", "Rohan Mehta", 260, 271, 0.98, "CONFIRMED"),
            ("EVD-002-SURV01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 310, 322, 0.98, "CONFIRMED"),
            ("EVD-002-SURV01", "Sunil Deshmukh", "PERSON", "Sunil Deshmukh", "Sunil Deshmukh", 338, 352, 0.98, "CONFIRMED"),
            ("EVD-002-SURV01", "MH-04-KT-2187", "VEHICLE", "MH-04-KT-2187", "MH-04-KT-2187", 210, 223, 0.99, "CONFIRMED"),
            ("EVD-002-SURV01", "Warehouse 14", "LOCATION", "Warehouse 14", "Warehouse 14", 120, 132, 0.98, "CONFIRMED"),

            # In EVD-002-INTEL01
            ("EVD-002-INTEL01", "Rohan Mehta", "PERSON", "Rohan Mehta", "Rohan Mehta", 140, 151, 0.98, "CONFIRMED"),
            ("EVD-002-INTEL01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 320, 332, 0.98, "CONFIRMED"),
            ("EVD-002-INTEL01", "Apex Logistics Mumbai", "ORGANIZATION", "Apex Logistics Mumbai", "Apex Logistics Mumbai", 80, 101, 0.99, "CONFIRMED"),
            ("EVD-002-INTEL01", "Warehouse 14", "LOCATION", "Warehouse 14", "Warehouse 14", 190, 202, 0.98, "CONFIRMED"),
            ("EVD-002-INTEL01", "ACC-LOGI-17", "ACCOUNT", "ACC-LOGI-17", "ACC-LOGI-17", 450, 461, 0.99, "CONFIRMED"),

            # In EVD-002-VEH01
            ("EVD-002-VEH01", "MH-04-KT-2187", "VEHICLE", "MH-04-KT-2187", "MH-04-KT-2187", 20, 33, 0.99, "CONFIRMED"),
            ("EVD-002-VEH01", "Sunil Deshmukh", "PERSON", "Sunil Deshmukh", "Sunil Deshmukh", 48, 62, 0.98, "CONFIRMED"),
            ("EVD-002-VEH01", "Rajesh Verma", "PERSON", "Rajesh Verma", "Rajesh Verma", 80, 92, 0.98, "CONFIRMED"),
            ("EVD-002-VEH01", "Warehouse 14", "LOCATION", "Warehouse 14", "Warehouse 14", 34, 46, 0.98, "CONFIRMED"),
            ("EVD-002-VEH01", "MIDC Industrial Estate", "LOCATION", "MIDC Industrial Estate", "MIDC Industrial Estate", 95, 117, 0.98, "CONFIRMED"),
            ("EVD-002-VEH01", "Andheri East", "LOCATION", "Andheri East", "Andheri East", 120, 132, 0.98, "CONFIRMED"),
        ]

        mentions_002 = {}
        for eid, ent_name, mtype, text, norm_val, start, end, conf, res_stat in mentions_data_002:
            evd = evidence_records_002[eid]
            ent = entities_002.get(ent_name)
            mkey = f"{eid}:{mtype}:{start}:{end}:{norm_val}"
            rec = EntityMentionRecord(
                evidence_id=evd.id,
                entity_id=ent.id if ent else None,
                mention_key=mkey,
                entity_type=mtype,
                text=text,
                normalized_value=norm_val,
                start=start,
                end=end,
                confidence=conf,
                resolution_status=res_stat,
                resolution_confidence=conf,
            )
            db.add(rec)
            db.flush()
            mentions_002[f"{eid}:{ent_name}"] = rec
            mentions_002[f"{eid}:{text}"] = rec

        # 4.4 Exactly 3 Ambiguous Mentions for Human-In-The-Loop Entity Resolution
        # Ambiguous 1: "R. Mehta" in EVD-002-FIR01
        m_r_mehta = EntityMentionRecord(
            evidence_id=evidence_records_002["EVD-002-FIR01"].id,
            entity_id=None,
            mention_key="EVD-002-FIR01:PERSON:820:828:R. Mehta",
            entity_type="PERSON",
            text="R. Mehta",
            normalized_value="R. Mehta",
            start=820,
            end=828,
            confidence=0.88,
            resolution_status="UNRESOLVED",
        )
        db.add(m_r_mehta)
        db.flush()

        # Ambiguous 2: "Apex Logistics" in EVD-002-INTEL01
        m_apex_short = EntityMentionRecord(
            evidence_id=evidence_records_002["EVD-002-INTEL01"].id,
            entity_id=None,
            mention_key="EVD-002-INTEL01:ORGANIZATION:510:524:Apex Logistics",
            entity_type="ORGANIZATION",
            text="Apex Logistics",
            normalized_value="Apex Logistics",
            start=510,
            end=524,
            confidence=0.91,
            resolution_status="UNRESOLVED",
        )
        db.add(m_apex_short)
        db.flush()

        # Ambiguous 3: "MH-04-KT-2187 (Commercial Van)" in EVD-002-SURV01
        m_veh_desc = EntityMentionRecord(
            evidence_id=evidence_records_002["EVD-002-SURV01"].id,
            entity_id=None,
            mention_key="EVD-002-SURV01:VEHICLE:160:190:MH-04-KT-2187 (Commercial Van)",
            entity_type="VEHICLE",
            text="MH-04-KT-2187 (Commercial Van)",
            normalized_value="MH-04-KT-2187",
            start=160,
            end=190,
            confidence=0.94,
            resolution_status="UNRESOLVED",
        )
        db.add(m_veh_desc)
        db.flush()

        # Target confirmed mentions
        m_rohan_fir = mentions_002["EVD-002-FIR01:Rohan Mehta"]
        m_apex_fir = mentions_002["EVD-002-FIR01:Apex Logistics Mumbai"]
        m_veh_fir = mentions_002["EVD-002-FIR01:MH-04-KT-2187"]

        # 4.5 Suggestions for Human Review
        db.add(
            EntityResolution(
                source_mention_id=m_r_mehta.id,
                target_mention_id=m_rohan_fir.id,
                confidence=0.88,
                reasons=["High name similarity (Levenshtein 0.89)", "Common phone link (+91 90000 32741)", "Same location context (Warehouse 14)"],
                status="SUGGESTED",
            )
        )
        db.add(
            EntityResolution(
                source_mention_id=m_apex_short.id,
                target_mention_id=m_apex_fir.id,
                confidence=0.91,
                reasons=["Substring match on organization name", "Matching primary address (Andheri East)", "Shared director (Rohan Mehta)"],
                status="SUGGESTED",
            )
        )
        db.add(
            EntityResolution(
                source_mention_id=m_veh_desc.id,
                target_mention_id=m_veh_fir.id,
                confidence=0.94,
                reasons=["Exact registration plate match", "Associated driver Sunil Deshmukh"],
                status="SUGGESTED",
            )
        )

        # 4.6 Relationships for CASE-002 (18 Meaningful Links)
        relations_data_002 = [
            ("EVD-002-FIR01", "Rohan Mehta", "Apex Logistics Mumbai", "DIRECTED", "Rohan Mehta manages freight operations for Apex Logistics Mumbai.", 0.98),
            ("EVD-002-FIR01", "Rajesh Verma", "Apex Logistics Mumbai", "WORKED_FOR", "Rajesh Verma coordinates logistics fleet for Apex Logistics Mumbai.", 0.97),
            ("EVD-002-SURV01", "Sunil Deshmukh", "MH-04-KT-2187", "OPERATED", "Sunil Deshmukh operates carrier vehicle MH-04-KT-2187.", 0.98),
            ("EVD-002-FIR01", "Rohan Mehta", "+91 90000 32741", "USED", "Primary contact telephone line used by Rohan Mehta.", 0.99),
            ("EVD-002-CDR01", "Rajesh Verma", "+91 90000 58126", "USED", "Registered mobile phone line used by Rajesh Verma.", 0.99),
            ("EVD-002-CDR01", "Apex Logistics Mumbai", "+91 90000 61483", "USED", "Commercial dispatch line used by Apex Logistics Mumbai.", 0.98),
            ("EVD-002-CDR01", "+91 90000 32741", "+91 90000 58126", "CONTACTED", "Frequent bilateral telecommunication contact between Rohan Mehta and Rajesh Verma.", 0.98),
            ("EVD-002-CDR01", "+91 90000 32741", "+91 90000 61483", "CONTACTED", "Telecommunication calls logged between Rohan Mehta and dispatch line.", 0.97),
            ("EVD-002-FIN01", "Rohan Mehta", "ACC-LOGI-17", "TRANSFERRED_TO", "High-value fund transfer of ₹4,80,000 from Rohan Mehta to corporate account ACC-LOGI-17.", 0.99),
            ("EVD-002-FIN01", "ACC-ROHAN-01", "ACC-LOGI-17", "TRANSFERRED_TO", "Direct electronic banking disbursement from ACC-ROHAN-01 to ACC-LOGI-17.", 0.99),
            ("EVD-002-FIN01", "ACC-LOGI-17", "ACC-SUPPLY-04", "TRANSFERRED_TO", "Disbursements from ACC-LOGI-17 to warehouse supplier account ACC-SUPPLY-04.", 0.97),
            ("EVD-002-SURV01", "Rohan Mehta", "Warehouse 14", "VISITED", "Rohan Mehta observed entering Warehouse 14 facility office on August 23.", 0.98),
            ("EVD-002-SURV01", "Rajesh Verma", "Warehouse 14", "VISITED", "Rajesh Verma observed at Warehouse 14 during evening loading window.", 0.98),
            ("EVD-002-VEH01", "MH-04-KT-2187", "Warehouse 14", "VISITED", "Commercial vehicle MH-04-KT-2187 logged entries at Warehouse 14.", 0.98),
            ("EVD-002-FIR01", "Warehouse 14", "MIDC Industrial Estate", "LOCATED_AT", "Warehouse 14 is located in Plot 14 of MIDC Industrial Estate.", 0.99),
            ("EVD-002-FIR01", "MIDC Industrial Estate", "Andheri East", "LOCATED_AT", "MIDC Industrial Estate is located in Andheri East, Mumbai.", 0.99),
            ("EVD-002-FIR01", "Arjun Deshmukh", "Warehouse 14", "SUPERVISED", "Arjun Deshmukh is the on-site supervisor at Warehouse 14.", 0.98),
            ("EVD-002-SURV01", "Rajesh Verma", "Rohan Mehta", "MET", "Surveillance officers observed rendezvous between Rajesh Verma and Rohan Mehta at Warehouse 14.", 0.98),
        ]

        for eid, src_ent, tgt_ent, rel_type, src_text, conf in relations_data_002:
            evd = evidence_records_002[eid]
            src_e = entities_002.get(src_ent)
            tgt_e = entities_002.get(tgt_ent)
            src_m = mentions_002.get(f"{eid}:{src_ent}") or next((m for k, m in mentions_002.items() if src_ent in k), None)
            tgt_m = mentions_002.get(f"{eid}:{tgt_ent}") or next((m for k, m in mentions_002.items() if tgt_ent in k), None)

            if src_e and tgt_e and src_m and tgt_m:
                db.add(
                    Relation(
                        case_id=case2.id,
                        evidence_id=evd.id,
                        source_entity_id=src_e.id,
                        target_entity_id=tgt_e.id,
                        source_mention_id=src_m.id,
                        target_mention_id=tgt_m.id,
                        relation_type=rel_type,
                        source_text=src_text,
                        confidence=conf,
                    )
                )

        # 4.7 Timeline Events for CASE-002 (10 Chronological Events across August 2026)
        timeline_events_002 = [
            (
                "EVD-002-CDR01",
                "CALL",
                "2026-08-08",
                "09:14",
                None,
                ["+91 90000 32741", "+91 90000 58126"],
                json.dumps({"timestamp": "2026-08-08T09:14:00", "caller": "+91 90000 32741", "receiver": "+91 90000 58126", "duration": "68", "cell_tower": "MIDC Industrial Estate"}),
                0.98,
                "EV-002-CDR01",
            ),
            (
                "EVD-002-FIN01",
                "FINANCIAL_TRANSACTION",
                "2026-08-10",
                "12:18",
                None,
                ["ACC-ROHAN-01", "ACC-LOGI-17"],
                json.dumps({"timestamp": "2026-08-10T12:18:00", "sender_account": "ACC-ROHAN-01", "receiver_account": "ACC-LOGI-17", "amount": "42000", "description": "Fleet maintenance advance"}),
                0.98,
                "EV-002-FIN01",
            ),
            (
                "EVD-002-VEH01",
                "VEHICLE_MOVEMENT",
                "2026-08-20",
                "08:42",
                "Warehouse 14",
                ["MH-04-KT-2187", "Sunil Deshmukh"],
                "Vehicle MH-04-KT-2187 dispatched to Warehouse 14 by driver Sunil Deshmukh for routine staging.",
                0.97,
                "EV-002-VEH01",
            ),
            (
                "EVD-002-CDR01",
                "CALL",
                "2026-08-21",
                "14:10",
                None,
                ["+91 90000 32741", "+91 90000 61483"],
                json.dumps({"timestamp": "2026-08-21T14:10:00", "caller": "+91 90000 32741", "receiver": "+91 90000 61483", "duration": "195", "cell_tower": "Andheri East"}),
                0.99,
                "EV-002-CDR02",
            ),
            (
                "EVD-002-VEH01",
                "VEHICLE_MOVEMENT",
                "2026-08-22",
                "14:15",
                "Andheri East",
                ["MH-04-KT-2187", "Rajesh Verma"],
                "Commercial vehicle MH-04-KT-2187 logged checkpoint transit in Andheri East operated by Rajesh Verma.",
                0.97,
                "EV-002-VEH02",
            ),
            (
                "EVD-002-FIN01",
                "FINANCIAL_TRANSACTION",
                "2026-08-23",
                "11:30",
                None,
                ["ACC-ROHAN-01", "ACC-LOGI-17"],
                json.dumps({"timestamp": "2026-08-23T11:30:00", "sender_account": "ACC-ROHAN-01", "receiver_account": "ACC-LOGI-17", "amount": "480000", "description": "Urgent consignment handling advance (Anomalous)"}),
                0.99,
                "EV-002-FIN02",
            ),
            (
                "EVD-002-VEH01",
                "VEHICLE_MOVEMENT",
                "2026-08-23",
                "21:05",
                "Warehouse 14",
                ["MH-04-KT-2187", "Rajesh Verma"],
                "Commercial carrier MH-04-KT-2187 arrived and entered Warehouse 14 through service access road.",
                0.98,
                "EV-002-VEH03",
            ),
            (
                "EVD-002-SURV01",
                "MEETING",
                "2026-08-23",
                "21:51",
                "Warehouse 14",
                ["Rohan Mehta", "Rajesh Verma", "Sunil Deshmukh"],
                "Rohan Mehta, Rajesh Verma, and driver Sunil Deshmukh met inside Warehouse 14 and supervised loading of freight into MH-04-KT-2187.",
                0.98,
                "EV-002-SURV01",
            ),
            (
                "EVD-002-FIR01",
                "INCIDENT",
                "2026-08-23",
                "22:40",
                "Warehouse 14",
                ["Rohan Mehta", "MH-04-KT-2187", "Arjun Deshmukh"],
                "Unauthorized departure and consignment diversion from Warehouse 14 without gate clearance.",
                0.99,
                "EV-002-INC01",
            ),
            (
                "EVD-002-FIR01",
                "LEGAL_FILING",
                "2026-08-24",
                "08:30",
                "Warehouse 14",
                ["Arjun Deshmukh", "Rohan Mehta"],
                "Formal registration of FIR No. 183/2026 at MIDC Police Station, Andheri East.",
                0.99,
                "EV-002-FIR01",
            ),
        ]

        for eid, ev_type, ev_date, ev_time, loc_name, part_names, src_text, conf, ev_key in timeline_events_002:
            evd = evidence_records_002[eid]
            loc_ent = entities_002.get(loc_name) if loc_name else None
            ev = Event(
                case_id=case2.id,
                evidence_id=evd.id,
                event_key=ev_key,
                event_type=ev_type,
                event_date=ev_date,
                event_time=ev_time,
                location_entity_id=loc_ent.id if loc_ent else None,
                source_text=src_text,
                confidence=conf,
            )
            db.add(ev)
            db.flush()

            for pname in part_names:
                m = mentions_002.get(f"{eid}:{pname}")
                if m:
                    db.add(EventParticipant(event_id=ev.id, mention_id=m.id))

        db.commit()
        print("Tesseract Full Seeding Completed Successfully:")
        print(f"CASE-001: {db.query(Evidence).filter(Evidence.case_id == case1.id).count()} evidence records")
        print(f"CASE-002: {db.query(Evidence).filter(Evidence.case_id == case2.id).count()} evidence records, {db.query(Entity).filter(Entity.case_id == case2.id).count()} entities, {db.query(Relation).filter(Relation.case_id == case2.id).count()} relations, {db.query(Event).filter(Event.case_id == case2.id).count()} events")
        print(f"CASE-003: Restricted investigation initialized with Lead INV-021.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
