import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import EvidenceIntegrity, uid


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk); size += len(chunk)
    return digest.hexdigest(), size


def ledger_record(evidence_id: str, digest: str, actor_id: str) -> tuple[str, dict]:
    record_id = f"LEDGER-{evidence_id}-{uid()[:8].upper()}"
    return record_id, {"recordId": record_id, "evidenceId": evidence_id, "sha256": digest, "algorithm": "SHA-256", "registeredAt": datetime.now(timezone.utc).isoformat(), "actorId": actor_id}


def register(path: Path, evidence_id: str, actor_id: str) -> EvidenceIntegrity:
    digest, size = sha256_file(path)
    record_id, _ = ledger_record(evidence_id, digest, actor_id)
    return EvidenceIntegrity(evidence_id=evidence_id, sha256=digest, file_size=size, ledger_record_id=record_id)
