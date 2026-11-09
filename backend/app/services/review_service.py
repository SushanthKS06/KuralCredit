from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ProviderError
from app.core.lifecycle import ApplicationStatus, assert_transition
from app.domain.provenance import ProvenanceStatus
from app.models.application import Application
from app.models.base import utcnow
from app.models.review import ReviewAction
from app.providers.interfaces import ReasoningProvider
from app.repositories.audit_repository import AuditRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.fact_repository import FactRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.application import ApplicationOut
from app.schemas.review import (
    ReviewActionOut,
    ReviewActionRequest,
    ReviewerApplicationOut,
    ReviewerQueueItem,
    ReviewerSummaryOut,
    ReviewQueueOut,
)
from app.services.application_service import ApplicationService
from app.services.audit_service import AuditService
from app.services.clarification_service import ClarificationService
from app.services.evidence_service import EvidenceService
from app.services.reconciliation_service import ReconciliationService
from app.services.serializers import (
    audit_out,
    clarification_out,
    document_out,
    fact_display_value,
    fact_out,
    review_action_out,
    turn_out,
)

logger = logging.getLogger(__name__)

REVIEWABLE_STATUSES = {
    ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
    ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS,
}
BOUNDARY_NOTICE = (
    "KuralCredit prepares and explains evidence only. It does not approve, reject, score, rank "
    "or recommend credit, and it does not determine fraud or eligibility. A human reviewer makes "
    "any decision. Differences shown here are neutral questions for context."
)
LIMITATIONS = [
    (
        "No credit decision, score, approval, rejection, fraud finding or eligibility "
        "determination is made."
    ),
    (
        "Bank credits are not revenue and may include transfers, loans, refunds and "
        "non-business deposits."
    ),
    "Applicant-provided documents are evidence, not independent verification.",
    "Missing data is not treated as zero.",
    "Comparisons use an explicit configured tolerance and are not an audit.",
]


class ReviewService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        reasoning: ReasoningProvider,
        application_service: ApplicationService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.reasoning = reasoning
        self.application_service = application_service
        self.reviews = ReviewRepository(db)
        self.facts = FactRepository(db)
        self.documents = DocumentRepository(db)
        self.conversations = ConversationRepository(db)
        self.audit_repository = AuditRepository(db)
        self.audit = AuditService(db)
        self.evidence = EvidenceService(db)
        self.reconciliation = ReconciliationService(db, settings.reconciliation_tolerance_percent)
        self.clarifications = ClarificationService(db, reasoning)

    def queue(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
        statuses: set[str] | None = None,
    ) -> ReviewQueueOut:
        selected = statuses or {status.value for status in REVIEWABLE_STATUSES}
        applications = self.reviews.queue(
            statuses=selected, query=query, limit=limit, offset=offset
        )
        total = self.reviews.queue_count(statuses=selected, query=query)
        items: list[ReviewerQueueItem] = []
        for application in applications:
            completeness = self.application_service.completeness(application)
            item_total = len(completeness.items)
            completed = sum(1 for item in completeness.items if item.complete)
            items.append(
                ReviewerQueueItem(
                    application_id=application.id,
                    reference=application.reference,
                    applicant_name=application.applicant_name,
                    business_name=application.business_name,
                    status=application.status,
                    submitted_at=application.submitted_at,
                    created_at=application.created_at,
                    open_clarifications=completeness.open_clarifications,
                    completeness_percent=round(completed / item_total * 100) if item_total else 0,
                    is_demo=application.is_demo,
                )
            )
        return ReviewQueueOut(items=items, total=total)

    def detail(self, application: Application) -> ReviewerApplicationOut:
        completeness = self.application_service.completeness(application)
        reconciliation = self.reconciliation.build(application)
        facts = self.facts.list_for_application(application.id)
        summary = self._summary(application, facts, reconciliation)
        return ReviewerApplicationOut(
            application=ApplicationOut.model_validate(application),
            completeness=completeness,
            facts=[fact_out(fact) for fact in facts],
            documents=[
                document_out(document)
                for document in self.documents.list_for_application(application.id)
            ],
            turns=[turn_out(turn) for turn in self.conversations.list_turns(application.id)],
            clarifications=[
                clarification_out(clarification)
                for clarification in self.conversations.list_clarifications(application.id)
            ],
            reconciliation=self.reconciliation.out(application),
            audit_events=[
                audit_out(event)
                for event in self.audit_repository.list_for_application(application.id)
            ],
            review_actions=[
                review_action_out(action) for action in self.reviews.list_actions(application.id)
            ],
            summary=summary,
            boundary_notice=BOUNDARY_NOTICE,
        )

    def act(
        self,
        application: Application,
        payload: ReviewActionRequest,
        reviewer_name: str,
    ) -> ReviewActionOut:
        status = ApplicationStatus(application.status)
        if status not in REVIEWABLE_STATUSES and status != ApplicationStatus.NEEDS_MORE_INFORMATION:
            raise ConflictError("This application is not in a reviewable state")
        if payload.action in {"verify_fact", "reject_fact"}:
            if status == ApplicationStatus.NEEDS_MORE_INFORMATION:
                raise ConflictError(
                    "Wait for the applicant to resubmit before changing fact verification"
                )
            assert payload.field_key is not None
            fact = self.facts.latest_for_field(application.id, payload.field_key)
            if fact is None:
                raise NotFoundError(f"No active financial fact found for {payload.field_key}")
            self._ensure_review_started(application, reviewer_name)
            if payload.action == "verify_fact":
                self.evidence.reviewer_verify(fact, reviewer_name, payload.reason)
            else:
                self.evidence.reviewer_reject(fact, reviewer_name, payload.reason)
            message = (
                f"Reviewer {'verified' if payload.action == 'verify_fact' else 'rejected'} "
                f"{payload.field_key}."
            )
        elif payload.action == "request_information":
            if status == ApplicationStatus.NEEDS_MORE_INFORMATION:
                raise ConflictError("The application is already waiting for more information")
            self._ensure_review_started(application, reviewer_name)
            self.clarifications.create_reviewer_request(
                application,
                reviewer_name=reviewer_name,
                field_key=payload.field_key,
                reason=payload.reason,
            )
            assert_transition(application.status, ApplicationStatus.NEEDS_MORE_INFORMATION)
            application.status = ApplicationStatus.NEEDS_MORE_INFORMATION.value
            message = "Reviewer requested more information from the applicant."
        elif payload.action == "complete_review":
            if status == ApplicationStatus.NEEDS_MORE_INFORMATION:
                raise ConflictError(
                    "Wait for the applicant to resubmit before completing the review"
                )
            if self.conversations.list_clarifications(application.id, status="open"):
                raise ConflictError("Open clarification questions must be answered first")
            self._ensure_review_started(application, reviewer_name)
            assert_transition(application.status, ApplicationStatus.REVIEW_COMPLETED)
            application.status = ApplicationStatus.REVIEW_COMPLETED.value
            application.review_completed_at = utcnow()
            message = (
                "Review marked complete. No credit decision was recorded; the human reviewer "
                "remains responsible for any decision."
            )
        else:
            raise ConflictError("Unsupported review action")

        action = ReviewAction(
            application_id=application.id,
            reviewer_name=reviewer_name,
            action=payload.action,
            field_key=payload.field_key,
            reason=payload.reason,
        )
        self.reviews.add_action(action)
        self.audit.record(
            application_id=application.id,
            actor=reviewer_name,
            event_type=f"review_{payload.action}",
            summary=message,
            detail={
                "action": payload.action,
                "field_key": payload.field_key,
                "reason": payload.reason,
                "application_status": application.status,
            },
        )
        self.db.commit()
        return review_action_out(action)

    def _ensure_review_started(self, application: Application, reviewer_name: str) -> None:
        if ApplicationStatus(application.status) == ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW:
            assert_transition(application.status, ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS)
            application.status = ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS.value
            self.audit.record(
                application_id=application.id,
                actor=reviewer_name,
                event_type="review_started",
                summary="Human review started. No automated decision is made.",
                detail={"from": "submitted_for_human_review"},
            )

    def _summary(
        self,
        application: Application,
        facts,
        reconciliation: dict[str, object],
    ) -> ReviewerSummaryOut:
        payload = [
            {
                "field_key": fact.field_key,
                "label": fact.label,
                "display_value": fact_display_value(fact),
                "provenance_status": fact.provenance_status,
                "source_type": fact.source_type,
                "source_locator": fact.source_locator,
            }
            for fact in facts
            if fact.provenance_status != ProvenanceStatus.REJECTED.value
        ]
        comparisons = [
            comparison
            for comparison in reconciliation.get("comparisons", [])
            if isinstance(comparison, dict)
        ]
        try:
            result = self.reasoning.reviewer_summary(
                facts=payload, comparisons=comparisons, limitations=LIMITATIONS
            )
            data = result.data
            return ReviewerSummaryOut(
                source="model",
                prompt_version=result.prompt_version,
                applicant_declared_facts=list(data.get("applicant_declared_facts") or []),
                document_derived_facts=list(data.get("document_derived_facts") or []),
                applicant_explanations=list(data.get("applicant_explanations") or []),
                unresolved_items=list(data.get("unresolved_items") or []),
                limitations=list(data.get("limitations") or LIMITATIONS),
                source_references=list(data.get("source_references") or []),
            )
        except ProviderError as exc:
            logger.warning(
                "reviewer_summary_fallback",
                extra={"extra_fields": {"error_code": exc.code}},
            )
        return self._fallback_summary(facts, comparisons)

    def _fallback_summary(self, facts, comparisons) -> ReviewerSummaryOut:
        declared: list[str] = []
        documents: list[str] = []
        explanations: list[str] = []
        references: list[str] = []
        for fact in facts:
            if fact.provenance_status == ProvenanceStatus.REJECTED.value:
                continue
            line = f"{fact.label}: {fact_display_value(fact)} ({fact.provenance_status})"
            if fact.source_type in {"bank_statement", "GST_document", "sales_register"}:
                documents.append(line)
            else:
                declared.append(line)
            if fact.source_locator:
                references.append(fact.source_locator)
        unresolved = [
            f"{item.get('left_label')} vs {item.get('right_label')}: {item.get('explanation')}"
            for item in comparisons
            if item.get("requires_clarification") or item.get("status") == "missing_information"
        ]
        return ReviewerSummaryOut(
            source="rule",
            prompt_version=None,
            applicant_declared_facts=declared,
            document_derived_facts=documents,
            applicant_explanations=explanations,
            unresolved_items=unresolved,
            limitations=LIMITATIONS,
            source_references=references,
        )
