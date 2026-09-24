from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import AuditEvent, now

def record(db: Session, *, actor_id: str | None, action: str, resource_type: str, resource_id: str | None = None, case_id: str | None = None, result: str = "SUCCESS", metadata: dict | None = None):
    if actor_id:
        cutoff = now() - timedelta(seconds=2)
        existing = db.scalar(
            select(AuditEvent).where(
                AuditEvent.actor_id == actor_id,
                AuditEvent.action == action,
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
                AuditEvent.timestamp >= cutoff
            )
        )
        if existing:
            return existing

    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        case_id=case_id,
        result=result,
        metadata_json=metadata or {}
    )
    db.add(event)
    return event
