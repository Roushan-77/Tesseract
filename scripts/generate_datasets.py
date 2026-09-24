import os
import json
import csv
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

BASE_DIR = Path(__file__).resolve().parent.parent
CASE_002_DIR = BASE_DIR / "seed" / "demo" / "final-case-002"
CASE_003_DIR = BASE_DIR / "seed" / "demo" / "final-case-003"

# Remove any existing files in final-case-002
if CASE_002_DIR.exists():
    for f in CASE_002_DIR.iterdir():
        if f.is_file():
            f.unlink()
CASE_002_DIR.mkdir(parents=True, exist_ok=True)
CASE_003_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()

header_style = ParagraphStyle(
    'DocHeader',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=13,
    leading=17,
    textColor=colors.HexColor('#0f172a'),
    spaceAfter=3
)

sub_header_style = ParagraphStyle(
    'DocSubHeader',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=9.5,
    leading=13,
    textColor=colors.HexColor('#475569'),
    spaceAfter=6
)

title_style = ParagraphStyle(
    'SectionTitle',
    parent=styles['Heading2'],
    fontName='Helvetica-Bold',
    fontSize=10.5,
    leading=14,
    textColor=colors.HexColor('#1e293b'),
    spaceBefore=6,
    spaceAfter=3
)

body_style = ParagraphStyle(
    'DocBody',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=9,
    leading=13,
    textColor=colors.HexColor('#334155'),
    spaceAfter=5
)

callout_style = ParagraphStyle(
    'Callout',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=8,
    leading=11,
    textColor=colors.HexColor('#64748b'),
    spaceBefore=4,
    spaceAfter=4
)

table_header_style = ParagraphStyle(
    'TableHeader',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=8,
    leading=11,
    textColor=colors.HexColor('#0f172a')
)

table_cell_style = ParagraphStyle(
    'TableCell',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=8,
    leading=11,
    textColor=colors.HexColor('#334155')
)


# ==========================================
# 1. CASE-002: FIR-183-2026.pdf
# ==========================================
def generate_fir_pdf():
    path = CASE_002_DIR / "FIR-183-2026.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []

    story.append(Paragraph("FIRST INFORMATION REPORT (FIR NO. 183/2026)", header_style))
    story.append(Paragraph("MIDC Police Station, Andheri East, Mumbai | Case Reference: CASE-002", sub_header_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

    meta_data = [
        [Paragraph("<b>FIR Number</b>", table_header_style), Paragraph("FIR-183-2026", table_cell_style), Paragraph("<b>Police Station</b>", table_header_style), Paragraph("MIDC Police Station", table_cell_style)],
        [Paragraph("<b>Registration Date</b>", table_header_style), Paragraph("24 August 2026", table_cell_style), Paragraph("<b>Incident Date & Time</b>", table_header_style), Paragraph("23 August 2026 at 22:40", table_cell_style)],
        [Paragraph("<b>Complainant Name</b>", table_header_style), Paragraph("Arjun Deshmukh", table_cell_style), Paragraph("<b>Place of Occurrence</b>", table_header_style), Paragraph("Warehouse 14, MIDC Industrial Estate, Andheri East", table_cell_style)],
        [Paragraph("<b>Complainant Phone</b>", table_header_style), Paragraph("+91 90000 18427", table_cell_style), Paragraph("<b>Applicable Law</b>", table_header_style), Paragraph("IPC Sections 457, 380, 34", table_cell_style)],
    ]
    t = Table(meta_data, colWidths=[110, 160, 110, 160])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("STATEMENT OF THE COMPLAINANT", title_style))
    statement = (
        "I, Arjun Deshmukh, employed as warehouse supervisor at Warehouse 14, MIDC Industrial Estate, Andheri East, "
        "report that on 23 August 2026 at approximately 22:40 hrs, an unauthorized consignment diversion occurred. "
        "High-value freight consignments registered under Apex Logistics Mumbai were unlawfully moved out of the warehouse premises.\n\n"
        "Security records log that suspect Rohan Mehta (contact: +91 90000 32741) and fleet coordinator Rajesh Verma "
        "coordinated the movement of commercial carrier vehicle MH-04-KT-2187 near the rear loading bay. "
        "The vehicle entered Warehouse 14 during evening hours and departed without standard gate clearance."
    )
    story.append(Paragraph(statement, body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("DOCUMENTED CLUES & PERSONS OF INTEREST", title_style))
    clues_data = [
        [Paragraph("<b>Entity</b>", table_header_style), Paragraph("<b>Identified Value</b>", table_header_style), Paragraph("<b>Context</b>", table_header_style)],
        [Paragraph("Primary Subject", table_cell_style), Paragraph("Rohan Mehta", table_cell_style), Paragraph("Operations Manager (Phone: +91 90000 32741)", table_cell_style)],
        [Paragraph("Logistics Associate", table_cell_style), Paragraph("Rajesh Verma", table_cell_style), Paragraph("Fleet Coordinator, Apex Logistics Mumbai", table_cell_style)],
        [Paragraph("Identified Vehicle", table_cell_style), Paragraph("MH-04-KT-2187", table_cell_style), Paragraph("Commercial carrier observed at Warehouse 14", table_cell_style)],
        [Paragraph("Incident Location", table_cell_style), Paragraph("Warehouse 14", table_cell_style), Paragraph("MIDC Industrial Estate, Andheri East", table_cell_style)],
    ]
    t2 = Table(clues_data, colWidths=[120, 160, 260])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t2)
    story.append(Spacer(1, 8))

    story.append(Paragraph("DISCLAIMER: Fictionalized synthetic investigation record for software evaluation in Tesseract.", callout_style))
    doc.build(story)
    print("Generated:", path)


# ==========================================
# 2. CASE-002: CDR-August-2026.csv
# ==========================================
def generate_cdr_csv():
    path = CASE_002_DIR / "CDR-August-2026.csv"
    headers = ["timestamp", "caller", "receiver", "duration_seconds", "cell_tower"]
    rows = [
        # Baseline calls (early August)
        ["2026-08-08T09:14:00", "+91 90000 32741", "+91 90000 58126", "68", "MIDC Industrial Estate"],
        ["2026-08-10T18:42:00", "+91 90000 58126", "+91 90000 32741", "91", "Andheri East"],
        ["2026-08-14T11:07:00", "+91 90000 32741", "+91 90000 58126", "45", "MIDC Industrial Estate"],
        ["2026-08-18T17:20:00", "+91 90000 58126", "+91 90000 32741", "78", "Andheri East"],

        # ANOMALY 1: COMMUNICATION SPIKE ON 21 AUGUST (8 calls surge)
        ["2026-08-21T09:15:00", "+91 90000 32741", "+91 90000 58126", "240", "Andheri East"],
        ["2026-08-21T10:45:00", "+91 90000 32741", "+91 90000 58126", "185", "MIDC Industrial Estate"],
        ["2026-08-21T12:30:00", "+91 90000 58126", "+91 90000 32741", "310", "MIDC Industrial Estate"],
        ["2026-08-21T14:10:00", "+91 90000 32741", "+91 90000 61483", "195", "Andheri East"],
        ["2026-08-21T16:25:00", "+91 90000 61483", "+91 90000 32741", "280", "Andheri East"],
        ["2026-08-21T18:40:00", "+91 90000 32741", "+91 90000 58126", "420", "MIDC Industrial Estate"],
        ["2026-08-21T21:15:00", "+91 90000 58126", "+91 90000 32741", "350", "MIDC Industrial Estate"],
        ["2026-08-21T23:40:00", "+91 90000 32741", "+91 90000 61483", "290", "Andheri East"],

        # Pre-incident and incident calls (22-23 August)
        ["2026-08-22T08:30:00", "+91 90000 32741", "+91 90000 58126", "160", "MIDC Industrial Estate"],
        ["2026-08-22T15:20:00", "+91 90000 32741", "+91 90000 61483", "145", "Andheri East"],
        ["2026-08-23T11:15:00", "+91 90000 32741", "+91 90000 58126", "190", "Andheri East"],
        ["2026-08-23T20:15:00", "+91 90000 32741", "+91 90000 58126", "260", "MIDC Industrial Estate"],
        ["2026-08-23T21:05:00", "+91 90000 32741", "+91 90000 61483", "180", "MIDC Industrial Estate"],
        ["2026-08-23T22:45:00", "+91 90000 58126", "+91 90000 32741", "340", "MIDC Industrial Estate"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print("Generated:", path)


# ==========================================
# 3. CASE-002: Financial-Transactions-August-2026.csv
# ==========================================
def generate_financial_csv():
    path = CASE_002_DIR / "Financial-Transactions-August-2026.csv"
    headers = ["timestamp", "sender_account", "receiver_account", "amount", "description"]
    rows = [
        ["2026-08-10T12:18:00", "ACC-ROHAN-01", "ACC-LOGI-17", "42000", "Fleet maintenance advance"],
        ["2026-08-14T15:42:00", "ACC-LOGI-17", "ACC-SUPPLY-04", "38500", "Warehouse supply settlement"],
        ["2026-08-18T11:20:00", "ACC-ROHAN-01", "ACC-LOGI-17", "45000", "Freight handling disbursement"],
        
        # ANOMALY 2: ANOMALOUS HIGH-VALUE TRANSACTION ON 23 AUGUST (11:30 hrs)
        ["2026-08-23T11:30:00", "ACC-ROHAN-01", "ACC-LOGI-17", "480000", "Urgent consignment handling advance (Anomalous)"],
        
        ["2026-08-23T14:45:00", "ACC-LOGI-17", "ACC-SUPPLY-04", "35000", "Special transit fuel advance"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print("Generated:", path)


# ==========================================
# 4. CASE-002: Surveillance-Report-01.pdf
# ==========================================
def generate_surveillance_pdf():
    path = CASE_002_DIR / "Surveillance-Report-01.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []

    story.append(Paragraph("SURVEILLANCE OBSERVATION LOG", header_style))
    story.append(Paragraph("Crime Branch Special Operations Squad | Case Reference: CASE-002", sub_header_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

    meta_data = [
        [Paragraph("<b>Date of Observation</b>", table_header_style), Paragraph("23 August 2026", table_cell_style), Paragraph("<b>Target Location</b>", table_header_style), Paragraph("Warehouse 14, MIDC Industrial Estate, Andheri East", table_cell_style)],
        [Paragraph("<b>Observation Window</b>", table_header_style), Paragraph("20:55 hrs to 22:50 hrs", table_cell_style), Paragraph("<b>Observed Vehicle</b>", table_header_style), Paragraph("White commercial carrier MH-04-KT-2187", table_cell_style)],
    ]
    t = Table(meta_data, colWidths=[120, 150, 120, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("FIELD OBSERVATIONS", title_style))
    narrative = (
        "On 23 August 2026 at 20:55 hrs, surveillance officers took position near the rear access point of Warehouse 14 in MIDC Industrial Estate, Andheri East.\n\n"
        "At 21:08 hrs, commercial vehicle MH-04-KT-2187 entered Warehouse 14 through the service road. "
        "Subject Rohan Mehta arrived on site at 21:34 hrs and entered the warehouse office. "
        "At 21:51 hrs, Rohan Mehta met with Rajesh Verma and driver Sunil Deshmukh. The subjects supervised the loading of crates into vehicle MH-04-KT-2187.\n\n"
        "At 22:40 hrs, loading was completed. At 22:47 hrs, vehicle MH-04-KT-2187 departed Warehouse 14 towards Andheri East."
    )
    story.append(Paragraph(narrative, body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("DISCLAIMER: Fictionalized synthetic investigation record for software evaluation in Tesseract.", callout_style))
    doc.build(story)
    print("Generated:", path)


# ==========================================
# 5. CASE-002: Field-Intelligence-Report.pdf
# ==========================================
def generate_field_intel_pdf():
    path = CASE_002_DIR / "Field-Intelligence-Report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []

    story.append(Paragraph("FIELD INTELLIGENCE NOTE", header_style))
    story.append(Paragraph("Special Intelligence Wing, Mumbai Suburban | Case Reference: CASE-002", sub_header_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

    meta_data = [
        [Paragraph("<b>Date of Report</b>", table_header_style), Paragraph("22 August 2026", table_cell_style), Paragraph("<b>Target Organization</b>", table_header_style), Paragraph("Apex Logistics Mumbai", table_cell_style)],
        [Paragraph("<b>Primary Subject</b>", table_header_style), Paragraph("Rohan Mehta", table_cell_style), Paragraph("<b>Target Facility</b>", table_header_style), Paragraph("Warehouse 14, MIDC Industrial Estate, Andheri East", table_cell_style)],
    ]
    t = Table(meta_data, colWidths=[120, 150, 120, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("INVESTIGATIVE LEADS", title_style))
    narrative = (
        "Field intelligence indicates that operations manager Rohan Mehta has coordinated unauthorized freight diversions "
        "for Apex Logistics Mumbai using storage space at Warehouse 14 in MIDC Industrial Estate, Andheri East.\n\n"
        "Technical subscriber analysis shows extensive telecommunication contact between Rohan Mehta (+91 90000 32741), "
        "fleet coordinator Rajesh Verma (+91 90000 58126), and field contact +91 90000 61483. "
        "A sharp communication spike occurred on 21 August 2026.\n\n"
        "CROSS-CASE LINKAGE: Corporate account ACC-LOGI-17 used by Apex Logistics Mumbai shares financial links with an offshore inquiry "
        "monitored by the Economic Offences Wing in CASE-003. Investigator INV-017 should submit an access request to CASE-003."
    )
    story.append(Paragraph(narrative, body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("DISCLAIMER: Fictionalized synthetic investigation record for software evaluation in Tesseract.", callout_style))
    doc.build(story)
    print("Generated:", path)


# ==========================================
# 6. CASE-002: Vehicle-Movement-Records.csv
# ==========================================
def generate_vehicle_csv():
    path = CASE_002_DIR / "Vehicle-Movement-Records.csv"
    headers = ["timestamp", "vehicle_number", "location", "driver"]
    rows = [
        ["2026-08-20T08:42:00", "MH-04-KT-2187", "Warehouse 14", "Sunil Deshmukh"],
        ["2026-08-20T17:30:00", "MH-04-KT-2187", "MIDC Industrial Estate", "Sunil Deshmukh"],
        ["2026-08-22T14:15:00", "MH-04-KT-2187", "Andheri East", "Rajesh Verma"],
        
        # TEMPORAL PATTERN: NIGHT MOVEMENT ON 23 AUGUST
        ["2026-08-23T21:05:00", "MH-04-KT-2187", "Warehouse 14", "Rajesh Verma"],
        ["2026-08-23T22:48:00", "MH-04-KT-2187", "Andheri East", "Rajesh Verma"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print("Generated:", path)


# ==========================================
# 7. CASE-002 README & MANIFEST
# ==========================================
def generate_case002_manifest_and_readme():
    manifest_path = CASE_002_DIR / "MANIFEST.json"
    manifest = {
        "case_id": "CASE-002",
        "title": "Mumbai Warehouse Network Investigation",
        "lead_investigator": "INV-017 (Inspector Rahul Mehta)",
        "file_count": 6,
        "files": [
            {
                "filename": "FIR-183-2026.pdf",
                "document_type": "PDF",
                "expected_processing_method": "OCR",
                "key_entities": ["Rohan Mehta", "Arjun Deshmukh", "Rajesh Verma", "Apex Logistics Mumbai", "Warehouse 14", "+91 90000 32741", "+91 90000 18427", "MH-04-KT-2187"]
            },
            {
                "filename": "CDR-August-2026.csv",
                "document_type": "CSV",
                "expected_processing_method": "Structured Parsing",
                "key_entities": ["+91 90000 32741", "+91 90000 58126", "+91 90000 61483", "MIDC Industrial Estate", "Andheri East"],
                "anomaly_intent": "Communication activity spike on 21 August 2026 (8 calls vs baseline of 1 call/day)"
            },
            {
                "filename": "Financial-Transactions-August-2026.csv",
                "document_type": "CSV",
                "expected_processing_method": "Structured Parsing",
                "key_entities": ["ACC-ROHAN-01", "ACC-LOGI-17", "ACC-SUPPLY-04"],
                "anomaly_intent": "Anomalous high-value transfer of ₹4,80,000 on 23 August 2026 at 11:30 hrs"
            },
            {
                "filename": "Surveillance-Report-01.pdf",
                "document_type": "PDF",
                "expected_processing_method": "OCR",
                "key_entities": ["Rohan Mehta", "Rajesh Verma", "Sunil Deshmukh", "Warehouse 14", "MH-04-KT-2187"]
            },
            {
                "filename": "Field-Intelligence-Report.pdf",
                "document_type": "PDF",
                "expected_processing_method": "OCR",
                "key_entities": ["Rohan Mehta", "Rajesh Verma", "Apex Logistics Mumbai", "Warehouse 14", "+91 90000 32741", "+91 90000 58126", "+91 90000 61483", "ACC-LOGI-17"],
                "cross_case_intent": "Shared link: ACC-LOGI-17 connected to restricted EOW inquiry CASE-003"
            },
            {
                "filename": "Vehicle-Movement-Records.csv",
                "document_type": "CSV",
                "expected_processing_method": "Structured Parsing",
                "key_entities": ["MH-04-KT-2187", "Sunil Deshmukh", "Rajesh Verma", "Warehouse 14", "Andheri East", "MIDC Industrial Estate"]
            }
        ]
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("Generated:", manifest_path)

    readme_path = CASE_002_DIR / "README.md"
    readme_content = """# CASE-002 Curated Synthetic Evidence Dataset — Mumbai Warehouse Network

This folder contains the highly coherent, curated **6-file dataset** for **CASE-002** (*Mumbai Warehouse Network Investigation*).

> **NOTE**: These files are saved as **STANDALONE FILES ONLY** outside application storage. They must be uploaded manually through the Tesseract UI to verify batch ingestion, automated OCR/parsing, integrity registration, and knowledge graph generation.

---

## 1. 6-File Inventory

| # | Filename | Format | Expected Ingestion Method | Role in Investigation |
|---|---|---|---|---|
| 1 | `FIR-183-2026.pdf` | PDF | **OCR** | Primary FIR registered at MIDC Police Station regarding unauthorized goods removal from Warehouse 14. |
| 2 | `CDR-August-2026.csv` | CSV | **Structured Parsing** | Telecommunication CDR logs showing baseline vs **Communication Surge on 21 August 2026**. |
| 3 | `Financial-Transactions-August-2026.csv` | CSV | **Structured Parsing** | Corporate bank ledger showing baseline disbursements vs **Anomalous ₹4,80,000 Transfer** on 23 August 2026. |
| 4 | `Surveillance-Report-01.pdf` | PDF | **OCR** | Special Squad surveillance log capturing pre-incident coordination at Warehouse 14. |
| 5 | `Field-Intelligence-Report.pdf` | PDF | **OCR** | Strategic intelligence memorandum identifying Apex Logistics Mumbai, key phone numbers, and cross-case link to `CASE-003`. |
| 6 | `Vehicle-Movement-Records.csv` | CSV | **Structured Parsing** | Fleet telematics and ANPR checkpoints showing night transit of vehicle `MH-04-KT-2187`. |

---

## 2. Core Entities (~15 Canonical Entities Total)

- **Persons (4)**: `Rohan Mehta`, `Rajesh Verma`, `Sunil Deshmukh`, `Arjun Deshmukh`.
- **Organizations (2)**: `Apex Logistics Mumbai`, `Malwa Freight Carriers`.
- **Phones (3)**: `+91 90000 32741`, `+91 90000 58126`, `+91 90000 61483`.
- **Vehicle (1)**: `MH-04-KT-2187`.
- **Locations (3)**: `Warehouse 14`, `MIDC Industrial Estate`, `Andheri East`.
- **Accounts (3)**: `ACC-ROHAN-01`, `ACC-LOGI-17`, `ACC-SUPPLY-04`.
- **Case IDs (2)**: `FIR-183-2026`, `CASE-002`.

---

## 3. Key Anomaly Patterns

1. **Communication Spike**: 8 calls surge on **21 August 2026** between Rohan Mehta, Rajesh Verma, and the field contact.
2. **Financial Spike**: Sudden **₹4,80,000** transfer from `ACC-ROHAN-01` to `ACC-LOGI-17` on **23 August 2026 at 11:30 hrs**.
3. **Temporal Cross-Source Pattern**: Communication surge (21 Aug) $\\rightarrow$ Wire transfer (23 Aug 11:30) $\\rightarrow$ Vehicle entry (23 Aug 21:05) $\\rightarrow$ Surveillance carton loading (21:34–22:40) $\\rightarrow$ Vehicle departure (22:48) $\\rightarrow$ FIR occurrence (22:40).
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("Generated:", readme_path)


# ==========================================
# 8. LIVE DEMO UPLOAD: Live-Field-Verification.pdf (Belongs to CASE-002)
# ==========================================
def generate_live_upload_pdf():
    live_pdf_path = CASE_002_DIR / "Live-Field-Verification.pdf"
    demo_root_pdf = BASE_DIR / "seed" / "demo" / "Live-Field-Verification.pdf"

    for path in [live_pdf_path, demo_root_pdf]:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph("SPECIAL FIELD VERIFICATION MEMORANDUM (DOC NO. VER-2026-094)", header_style))
        story.append(Paragraph("Mumbai Suburban Crime Branch, Special Operations Squad | Case Reference: CASE-002", sub_header_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

        story.append(Paragraph("INVESTIGATION VERIFICATION SUMMARY", title_style))
        summary_text = (
            "On 25 August 2026 at 15:30 hrs, verification officers conducted physical surveillance in Andheri East, Mumbai, "
            "regarding post-incident logistics activity connected to FIR-183/2026.\n\n"
            "Subject identified as R. Mehta (contact telephone: +91 90000 32741) "
            "was observed coordinating freight transit for commercial carrier MH-04-KT-2187 on behalf of Apex Logistics. "
            "The subject reviewed logistics manifests near the Andheri East facility before vehicle departure towards Warehouse 14.\n\n"
            "INVESTIGATIVE CORROBORATION: This record confirms ongoing coordination between R. Mehta and Apex Logistics fleet operations in Andheri East."
        )
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 8))

        story.append(Paragraph("RECORDED CLUES & ENTITIES", title_style))
        clues_data = [
            [Paragraph("<b>Target Subject</b>", table_header_style), Paragraph("R. Mehta", table_cell_style), Paragraph("<b>Target Location</b>", table_header_style), Paragraph("Andheri East", table_cell_style)],
            [Paragraph("<b>Organization</b>", table_header_style), Paragraph("Apex Logistics", table_cell_style), Paragraph("<b>Carrier Vehicle</b>", table_header_style), Paragraph("MH-04-KT-2187", table_cell_style)],
            [Paragraph("<b>Contact Phone</b>", table_header_style), Paragraph("+91 90000 32741", table_cell_style), Paragraph("<b>Verification Date</b>", table_header_style), Paragraph("25 August 2026", table_cell_style)],
        ]
        t = Table(clues_data, colWidths=[110, 160, 110, 160])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bae6fd')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

        story.append(Paragraph("DISCLAIMER: Synthetic investigative document for Tesseract demonstration.", callout_style))
        doc.build(story)
        print("Generated Live Demo File:", path)


# ==========================================
# 9. CASE-003: Restricted Case Notes
# ==========================================
def clean_case003():
    if CASE_003_DIR.exists():
        for f in CASE_003_DIR.iterdir():
            if f.is_file():
                f.unlink()
    CASE_003_DIR.mkdir(parents=True, exist_ok=True)
    readme_path = CASE_003_DIR / "README.md"
    readme_content = """# CASE-003 Restricted Inquiry Shell

CASE-003 (*Restricted Financial Network Investigation*) is a restricted related investigation shell used exclusively for demonstrating:
- Cross-case restriction indicators in CASE-002
- Investigator Access Request workflow (`POST /access-requests`)
- Lead Investigator authorization (`GRANT` / `DENY`)
- Immutable audit event logging

> **NOTE**: No separate evidence dataset is generated or preloaded for CASE-003. The live upload demo takes place on CASE-002 using `Live-Field-Verification.pdf`.
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("Generated CASE-003 README")


if __name__ == "__main__":
    generate_fir_pdf()
    generate_cdr_csv()
    generate_financial_csv()
    generate_surveillance_pdf()
    generate_field_intel_pdf()
    generate_vehicle_csv()
    generate_case002_manifest_and_readme()
    generate_live_upload_pdf()
    clean_case003()
    print("Curated datasets generated successfully!")
