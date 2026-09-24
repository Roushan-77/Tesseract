from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import AccessRequest, Case, CaseAssignment, User

def has_case_access(db: Session, user: User, case: Case) -> bool:
    assigned = db.scalar(select(CaseAssignment.id).where(CaseAssignment.case_id == case.id, CaseAssignment.user_id == user.id))
    if assigned: return True
    granted = db.scalar(select(AccessRequest.id).where(AccessRequest.case_id == case.id, AccessRequest.requester_id == user.id, AccessRequest.status == "GRANTED"))
    return granted is not None

def is_case_lead(case: Case, user: User) -> bool:
    return case.lead_investigator_id == user.id
