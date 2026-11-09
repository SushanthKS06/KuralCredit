from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ProviderError
from app.models.application import Application
from app.models.clarification import Clarification
from app.providers.interfaces import ReasoningProvider
from app.repositories.conversation_repository import ConversationRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

FALLBACK_QUESTIONS = {
    "declared_sales_vs_gst_turnover_difference": (
        "Your declared sales and GST turnover differ by more than the configured tolerance. "
        "Could you explain any timing, exemptions, or credit sales that a reviewer should know?"
    ),
    "declared_sales_vs_bank_credit_context": (
        "Bank credits are not the same as sales. Could you explain what is included in the "
        "bank credits, such as customer receipts, transfers, loans, or cash deposits?"
    ),
    "gst_turnover_vs_bank_credit_context": (
        "GST turnover and bank credits measure different things. Could you explain the main "
        "differences a reviewer should understand?"
    ),
    "cash_sales_vs_bank_credit_context": (
        "Cash sales may not pass through the bank account. Could you explain how cash sales are "
        "recorded and whether they are deposited?"
    ),
}

FIELD_PRIORITY = {
    "declared_sales_vs_gst_turnover_difference": 100,
    "declared_sales_vs_bank_credit_context": 110,
    "gst_turnover_vs_bank_credit_context": 120,
    "cash_sales_vs_bank_credit_context": 130,
}


class ClarificationService:
    def __init__(self, db: Session, reasoning: ReasoningProvider) -> None:
        self.db = db
        self.reasoning = reasoning
        self.conversations = ConversationRepository(db)
        self.audit = AuditService(db)

    def ensure_for_reconciliation(
        self,
        application: Application,
        reconciliation: dict[str, object],
        known_facts: list[dict[str, str]],
        actor: str,
    ) -> list[Clarification]:
        created: list[Clarification] = []
        comparisons = reconciliation.get("comparisons") or []
        for comparison in comparisons:
            if not isinstance(comparison, dict):
                continue
            if not comparison.get("requires_clarification"):
                continue
            field_key = str(comparison.get("clarification_field") or "").strip()
            if not field_key:
                continue
            if self.conversations.open_clarification_for_field(application.id, field_key):
                continue
            if any(
                clarification.field_key == field_key
                for clarification in self.conversations.list_clarifications(
                    application.id, status="answered"
                )
            ):
                continue
            reason = str(
                comparison.get("clarification_reason") or comparison.get("explanation") or ""
            )
            question, source, language = self._generate_question(
                application=application,
                field_key=field_key,
                reason=reason,
                known_facts=known_facts,
                expected_answer_type="text",
            )
            clarification = Clarification(
                application_id=application.id,
                field_key=field_key,
                question_text=question,
                reason=reason,
                expected_answer_type="text",
                status="open",
                priority=FIELD_PRIORITY.get(field_key, 200),
                source=source,
                language=language,
            )
            self.conversations.add_clarification(clarification)
            self.audit.record(
                application_id=application.id,
                actor=actor,
                event_type="clarification_created",
                summary="A neutral clarification question was created.",
                detail={
                    "clarification_id": clarification.id,
                    "field_key": field_key,
                    "source": source,
                },
            )
            created.append(clarification)
        return created

    def create_reviewer_request(
        self,
        application: Application,
        *,
        reviewer_name: str,
        field_key: str | None,
        reason: str,
    ) -> Clarification:
        resolved_field = field_key or "reviewer_information_request"
        clarification = Clarification(
            application_id=application.id,
            field_key=resolved_field,
            question_text=(f"A reviewer has requested additional information. Reason: {reason}"),
            reason=reason,
            expected_answer_type="text",
            status="open",
            priority=10,
            source="reviewer",
            language=application.language,
        )
        self.conversations.add_clarification(clarification)
        self.audit.record(
            application_id=application.id,
            actor=reviewer_name,
            event_type="reviewer_information_requested",
            summary="Reviewer requested additional information from the applicant.",
            detail={
                "clarification_id": clarification.id,
                "field_key": resolved_field,
                "reason": reason,
            },
        )
        return clarification

    def mark_answered(self, clarification: Clarification, turn_id: str, actor: str) -> None:
        from app.models.base import utcnow

        clarification.status = "answered"
        clarification.answered_at = utcnow()
        clarification.answer_turn_id = turn_id
        self.audit.record(
            application_id=clarification.application_id,
            actor=actor,
            event_type="clarification_answered",
            summary="Applicant answered a clarification question.",
            detail={
                "clarification_id": clarification.id,
                "field_key": clarification.field_key,
                "turn_id": turn_id,
            },
        )

    def _generate_question(
        self,
        *,
        application: Application,
        field_key: str,
        reason: str,
        known_facts: list[dict[str, str]],
        expected_answer_type: str,
    ) -> tuple[str, str, str]:
        try:
            result = self.reasoning.generate_clarification(
                field_key=field_key,
                reason=reason,
                known_facts=known_facts,
                language=application.language,
                expected_answer_type=expected_answer_type,
            )
            question = str(result.data.get("question") or "").strip()
            if question:
                return question, "model", application.language
            logger.warning("clarification_empty_model_response")
        except ProviderError as exc:
            logger.warning(
                "clarification_provider_fallback",
                extra={"extra_fields": {"error_code": exc.code}},
            )
        fallback = FALLBACK_QUESTIONS.get(
            field_key,
            "Could you provide more context for a human reviewer? "
            "This question is not a finding of a problem.",
        )
        note = (
            " Automatic translation was unavailable, so this fallback question is in English."
            if application.language != "en-IN"
            else ""
        )
        return fallback + note, "rule", "en-IN"
