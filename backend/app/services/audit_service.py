from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.observability.redaction import redact_value
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuditRepository(db)

    def record(
        self,
        *,
        application_id: str | None,
        actor: str,
        event_type: str,
        summary: str,
        detail: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            application_id=application_id,
            actor=actor,
            event_type=event_type,
            summary=summary,
            detail_json=redact_value(detail or {}),
        )
        return self.repository.add(event)

    def list_for_application(self, application_id: str) -> list[AuditEvent]:
        return self.repository.list_for_application(application_id)
