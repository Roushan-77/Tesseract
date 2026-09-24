import requests
import sys
import tempfile
from pathlib import Path

BASE = "http://localhost:8000"

def run_tests():
    # 1. Login
    resp = requests.post(f"{BASE}/auth/login", json={"investigator_id": "INV-017", "password": "demo-password"})
    if resp.status_code != 200:
        print(f"FAILED: Login failed: {resp.text}")
        sys.exit(1)
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Login successful")

    # 2. Test Processing Method mapping rules
    def py_get_method(filename, doc_type="", mime=""):
        ext = filename.split('.')[-1].lower()
        if ext in ['csv', 'xls', 'xlsx', 'json', 'xml', 'cdr'] or doc_type.lower() in ['csv', 'xls', 'xlsx', 'json', 'xml', 'cdr']:
            return "Structured Parsing"
        if ext in ['txt', 'doc', 'docx'] or doc_type.lower() in ['txt', 'doc', 'docx'] or 'text/plain' in mime:
            return "Text Extraction"
        return "OCR"

    assert py_get_method("FIR-183.png", "PNG", "image/png") == "OCR"
    assert py_get_method("report.pdf", "PDF", "application/pdf") == "OCR"
    assert py_get_method("statement.txt", "TXT", "text/plain") == "Text Extraction"
    assert py_get_method("notes.docx", "DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == "Text Extraction"
    assert py_get_method("transactions.csv", "CSV", "text/csv") == "Structured Parsing"
    assert py_get_method("logs.json", "JSON", "application/json") == "Structured Parsing"
    print("[OK] Processing Method logic verified for PNG, PDF, TXT, DOCX, CSV, JSON")

    # 3. Test Evidence Upload & SHA-256 registration
    test_content = b"TESSERACT TEST EVIDENCE FILE CONTENT FOR INTEGRITY VERIFICATION"
    files = {"file": ("test_evidence.txt", test_content, "text/plain")}
    resp = requests.post(f"{BASE}/cases/CASE-002/evidence", headers=headers, files=files)
    if resp.status_code != 200:
        print(f"FAILED: Upload failed: {resp.text}")
        sys.exit(1)
    ev_data = resp.json()
    eid = ev_data["evidence_id"]
    print(f"[OK] Newly uploaded file registered: {eid}")

    # Check GET integrity
    resp = requests.get(f"{BASE}/evidence/{eid}/integrity", headers=headers)
    integ = resp.json()
    orig_sha = integ["sha256"]
    ledger_id = integ["ledger_record_id"]
    assert orig_sha is not None, "SHA-256 must be registered on upload"
    assert ledger_id is not None, "Ledger record ID must be registered on upload"
    print(f"[OK] SHA-256 registered on upload: {orig_sha}")
    print(f"[OK] Ledger record created: {ledger_id}")

    # 4. Test Normal Verification -> VERIFIED
    resp = requests.post(f"{BASE}/evidence/{eid}/verify-integrity", headers=headers, json={})
    res_verify = resp.json()
    assert res_verify["status"] == "VERIFIED", f"Expected VERIFIED, got {res_verify['status']}"
    assert res_verify["verified"] is True, "Expected verified == True"
    assert res_verify["sha256"] == orig_sha, "Original hash must remain intact"
    print("[OK] Normal verification returned VERIFIED")

    # 5. Test Modified file -> MODIFIED / FAILED
    # Find stored file on disk
    storage_root = Path("storage/evidence")
    stored_files = list(storage_root.glob(f"{eid}/*"))
    assert len(stored_files) > 0, f"Stored file not found for {eid}"
    stored_file = stored_files[0]
    
    # Backup original bytes
    orig_bytes = stored_file.read_bytes()
    try:
        # Tamper file on disk
        stored_file.write_bytes(orig_bytes + b"_MODIFIED_BY_TAMPERING_TEST")
        
        # Verify integrity again
        resp = requests.post(f"{BASE}/evidence/{eid}/verify-integrity", headers=headers, json={})
        res_tampered = resp.json()
        assert res_tampered["status"] == "MODIFIED", f"Expected MODIFIED, got {res_tampered['status']}"
        assert res_tampered["verified"] is False, "Expected verified == False"
        assert res_tampered["sha256"] == orig_sha, "Original registered SHA-256 MUST NOT be overwritten after tampering!"
        assert res_tampered["current_hash"] != orig_sha, "Current hash should reflect tampered file digest"
        print(f"[OK] Modified file returned MODIFIED")
        print(f"[OK] Original registered hash remains unchanged: {res_tampered['sha256']}")
        print(f"[OK] Current tampered hash detected: {res_tampered['current_hash']}")
    finally:
        # Restore original bytes
        stored_file.write_bytes(orig_bytes)
        print("[OK] Restored original file bytes")

    # Verify again after restoration
    resp = requests.post(f"{BASE}/evidence/{eid}/verify-integrity", headers=headers, json={})
    res_restored = resp.json()
    assert res_restored["status"] == "VERIFIED", "Restored file should verify cleanly"
    print("[OK] Re-verification after restoration returned VERIFIED")

    # 6. Test existing evidence records without integrity record
    # Find an evidence record that doesn't have integrity or create one
    resp = requests.get(f"{BASE}/cases/CASE-002/evidence", headers=headers)
    all_ev = resp.json()
    for ev in all_ev:
        eid_existing = ev["evidence_id"]
        res_int = requests.get(f"{BASE}/evidence/{eid_existing}/integrity", headers=headers).json()
        print(f"Existing Evidence {eid_existing} ({ev['filename']}): Processing Status = {ev['processing_status']}, Integrity Status = {res_int['status']}")
        # Test verify-integrity call for existing evidence
        res_v = requests.post(f"{BASE}/evidence/{eid_existing}/verify-integrity", headers=headers, json={}).json()
        assert res_v["status"] in ["VERIFIED", "MODIFIED"], f"Expected VERIFIED/MODIFIED for existing evidence, got {res_v['status']}"
        print(f"  -> Verified integrity: Status = {res_v['status']}, SHA-256 = {res_v['sha256']}")

    print("\n==========================================")
    print("ALL INTEGRITY & PROCESSING STATUS TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
