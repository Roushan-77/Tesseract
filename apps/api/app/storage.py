from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from .config import settings

STORAGE_ROOT = Path(settings.storage_root).resolve() if settings.storage_root else Path(__file__).resolve().parents[3] / "storage" / "evidence"
MIME_TYPES_BY_EXTENSION = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg", "image/pjpeg"},
    ".jpeg": {"image/jpeg", "image/pjpeg"},
    ".png": {"image/png", "image/x-png"},
    ".txt": {"text/plain"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".csv": {"text/csv", "application/csv"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".json": {"application/json", "text/json"},
    ".xml": {"application/xml", "text/xml"},
}
EXTENSIONS = set(MIME_TYPES_BY_EXTENSION)

def save_upload(evidence_id: str, upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if suffix not in EXTENSIONS or content_type not in MIME_TYPES_BY_EXTENSION[suffix]:
        raise ValueError("Only PDF, JPG, JPEG, PNG, TXT, DOC, DOCX, CSV, XLS, XLSX, JSON, and XML files are accepted")
    folder = STORAGE_ROOT / evidence_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{uuid4().hex}{suffix}"
    with destination.open("wb") as target:
        while chunk := upload.file.read(1024 * 1024): target.write(chunk)
    return str(destination.relative_to(STORAGE_ROOT)).replace("\\", "/")

def resolve_storage_key(key: str) -> Path:
    target = (STORAGE_ROOT / key).resolve()
    if STORAGE_ROOT.resolve() not in target.parents: raise ValueError("Invalid evidence path")
    return target
