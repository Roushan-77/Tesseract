import sys
from pathlib import Path
import urllib.request
import json

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.database import SessionLocal
from app.models import User
from app.security import token_for

db = SessionLocal()
u = db.query(User).filter(User.investigator_id == 'INV-017').first()
token = token_for(u)

pdf_path = (Path(__file__).resolve().parents[1] / "seed" / "demo" / "Live-Field-Verification.pdf")
boundary = "----WebKitFormBoundaryTest12345"

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="files"; filename="Live-Field-Verification.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode("utf-8") + pdf_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8000/cases/CASE-002/evidence",
    data=body,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as res:
        print("Upload Status:", res.status)
        data = json.loads(res.read().decode())
        print("Response:", data.get("evidence_id"), data.get("filename"), data.get("processing_status"))
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode())
except Exception as e:
    print("Error:", e)
finally:
    db.close()
