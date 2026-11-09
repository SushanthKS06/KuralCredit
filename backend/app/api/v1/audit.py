from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_dep, get_readable_application
from app.models.application import Application
from app.schemas.audit import AuditListOut
from app.services.audit_service import AuditService
from app.services.serializers import audit_out

router = APIRouter(tags=["audit"])


@router.get("/applications/{application_id}/audit", response_model=AuditListOut)
def get_audit(
    application: Application = Depends(get_readable_application),
    db: Session = Depends(get_db_dep),
) -> AuditListOut:
    events = AuditService(db).list_for_application(application.id)
    return AuditListOut(items=[audit_out(event) for event in events])
