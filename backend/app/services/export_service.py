from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.provenance import ProvenanceStatus
from app.models.application import Application
from app.observability.redaction import redact_text
from app.repositories.audit_repository import AuditRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.fact_repository import FactRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.application import ApplicationOut
from app.services.application_service import ApplicationService
from app.services.reconciliation_service import ReconciliationService
from app.services.review_service import BOUNDARY_NOTICE, LIMITATIONS
from app.services.serializers import (
    audit_out,
    clarification_out,
    document_out,
    fact_out,
    review_action_out,
    turn_out,
)


class ExportService:
    def __init__(
        self,
        db: Session,
        application_service: ApplicationService,
        reconciliation: ReconciliationService,
    ) -> None:
        self.db = db
        self.application_service = application_service
        self.reconciliation = reconciliation
        self.facts = FactRepository(db)
        self.documents = DocumentRepository(db)
        self.turns = ConversationRepository(db)
        self.audit = AuditRepository(db)
        self.reviews = ReviewRepository(db)

    def reviewer_packet(self, application: Application) -> dict[str, object]:
        facts = self.facts.list_for_application(application.id)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "boundary_notice": BOUNDARY_NOTICE,
            "limitations": LIMITATIONS,
            "application": ApplicationOut.model_validate(application).model_dump(mode="json"),
            "completeness": self.application_service.completeness(application).model_dump(
                mode="json"
            ),
            "facts": [fact_out(fact).model_dump(mode="json") for fact in facts],
            "documents": [
                document_out(document).model_dump(mode="json")
                for document in self.documents.list_for_application(application.id)
            ],
            "conversation_turns": [
                {
                    **turn_out(turn).model_dump(mode="json"),
                    "transcript": redact_text(turn.transcript),
                }
                for turn in self.turns.list_turns(application.id)
            ],
            "clarifications": [
                clarification_out(clarification).model_dump(mode="json")
                for clarification in self.turns.list_clarifications(application.id)
            ],
            "reconciliation": self.reconciliation.out(application).model_dump(mode="json"),
            "review_actions": [
                review_action_out(action).model_dump(mode="json")
                for action in self.reviews.list_actions(application.id)
            ],
            "audit_events": [
                audit_out(event).model_dump(mode="json")
                for event in self.audit.list_for_application(application.id)
            ],
            "rejected_fact_count": sum(
                1 for fact in facts if fact.provenance_status == ProvenanceStatus.REJECTED.value
            ),
        }
