# CASE-002 Curated Synthetic Evidence Dataset — Mumbai Warehouse Network

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
3. **Temporal Cross-Source Pattern**: Communication surge (21 Aug) $\rightarrow$ Wire transfer (23 Aug 11:30) $\rightarrow$ Vehicle entry (23 Aug 21:05) $\rightarrow$ Surveillance carton loading (21:34–22:40) $\rightarrow$ Vehicle departure (22:48) $\rightarrow$ FIR occurrence (22:40).
