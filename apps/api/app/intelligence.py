import hashlib

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from .models import Entity, EntityMentionRecord, EntityResolution, Event, EventParticipant, Relation, uid
from .prompt4 import resolution_suggestion, transliteration_key


def _mention_key(mention: dict) -> str:
    return f"{mention['type']}:{mention['start']}:{mention['end']}:{mention['normalizedValue']}"


def _as_dict(mention: EntityMentionRecord) -> dict:
    return {"type": mention.entity_type, "text": mention.text, "normalizedValue": mention.normalized_value, "start": mention.start, "end": mention.end}


def reconcile_prompt4(db: Session, evidence, result: dict) -> None:
    old_ids = list(db.scalars(select(EntityMentionRecord.id).where(EntityMentionRecord.evidence_id == evidence.id)))
    if old_ids:
        db.execute(delete(EntityResolution).where(or_(EntityResolution.source_mention_id.in_(old_ids), EntityResolution.target_mention_id.in_(old_ids))))
    db.execute(delete(Relation).where(Relation.evidence_id == evidence.id))
    old_event_ids = list(db.scalars(select(Event.id).where(Event.evidence_id == evidence.id)))
    if old_event_ids:
        db.execute(delete(EventParticipant).where(EventParticipant.event_id.in_(old_event_ids)))
    db.execute(delete(Event).where(Event.evidence_id == evidence.id))
    db.execute(delete(EntityMentionRecord).where(EntityMentionRecord.evidence_id == evidence.id))
    for entity in db.scalars(select(Entity).where(Entity.case_id == evidence.case_id)).all():
        has_mentions = db.scalar(select(EntityMentionRecord.id).where(EntityMentionRecord.entity_id == entity.id).limit(1)) is not None
        has_relations = db.scalar(select(Relation.id).where(or_(Relation.source_entity_id == entity.id, Relation.target_entity_id == entity.id)).limit(1)) is not None
        has_events = db.scalar(select(Event.id).where(Event.location_entity_id == entity.id).limit(1)) is not None
        has_participants = db.scalar(select(EventParticipant.id).join(EntityMentionRecord, EventParticipant.mention_id == EntityMentionRecord.id).where(EntityMentionRecord.entity_id == entity.id).limit(1)) is not None
        if not (has_mentions or has_relations or has_events or has_participants):
            db.delete(entity)
    db.flush()

    records: dict[str, EntityMentionRecord] = {}
    for raw in result.get("entities", []):
        key = _mention_key(raw)
        identity_key = transliteration_key(raw["normalizedValue"])
        entity = None
        if raw["type"] in {"PHONE", "VEHICLE"}:
            entity = db.scalar(select(Entity).where(Entity.case_id == evidence.case_id, Entity.entity_type == raw["type"], Entity.metadata_json["identity_key"].as_string() == identity_key))
        if entity is None:
            entity = Entity(case_id=evidence.case_id, entity_type=raw["type"], canonical_name=raw["text"], metadata_json={"identity_key": identity_key})
            db.add(entity)
            db.flush()
        record = EntityMentionRecord(evidence_id=evidence.id, entity_id=entity.id, mention_key=key, entity_type=raw["type"], text=raw["text"], normalized_value=raw["normalizedValue"], start=raw["start"], end=raw["end"], confidence=raw["confidence"], resolution_status="UNRESOLVED")
        db.add(record)
        records[key] = record
    db.flush()

    existing = list(db.scalars(select(EntityMentionRecord).join(EntityMentionRecord.evidence).where(EntityMentionRecord.evidence_id != evidence.id, EntityMentionRecord.evidence.has(case_id=evidence.case_id))))
    current = list(records.values())
    for source in current:
        for target in existing:
            suggestion = resolution_suggestion(_as_dict(source), _as_dict(target))
            if suggestion:
                db.add(EntityResolution(source_mention_id=source.id, target_mention_id=target.id, confidence=suggestion["confidence"], reasons=suggestion["reasons"], status="SUGGESTED"))

    for raw in result.get("relations", []):
        source = records.get(_mention_key(raw["source"]))
        target = records.get(_mention_key(raw["target"]))
        if source and target:
            db.add(Relation(case_id=evidence.case_id, evidence_id=evidence.id, source_entity_id=source.entity_id, target_entity_id=target.entity_id, source_mention_id=source.id, target_mention_id=target.id, relation_type=raw["type"], source_text=raw["sourceText"], confidence=raw["confidence"], source_row=raw.get("sourceRow"), source_fields=raw.get("sourceFields")))

    for raw in result.get("events", []):
        participants = [records[_mention_key(mention)] for mention in raw["participants"] if _mention_key(mention) in records]
        location = records.get(_mention_key(raw["location"])) if raw.get("location") else None
        event_key = f"{raw['type']}:{raw.get('sourceRow', 0)}:{hashlib.sha256(raw['sourceText'].encode('utf-8')).hexdigest()[:32]}"
        event = Event(case_id=evidence.case_id, evidence_id=evidence.id, event_key=event_key, event_type=raw["type"], event_date=raw.get("date"), location_entity_id=location.entity_id if location else None, source_text=raw["sourceText"], confidence=raw["confidence"], source_row=raw.get("sourceRow"), source_fields=raw.get("sourceFields"))
        db.add(event)
        db.flush()
        for participant in participants:
            db.add(EventParticipant(event_id=event.id, mention_id=participant.id))
