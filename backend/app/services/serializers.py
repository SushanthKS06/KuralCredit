from __future__ import annotations

from app.domain.fact_definitions import FACT_DEFINITIONS, FINANCIAL_MEASURES
from app.domain.money import format_inr, to_decimal
from app.domain.period import period_from_dates
from app.models.audit_event import AuditEvent
from app.models.clarification import Clarification
from app.models.conversation_turn import ConversationTurn
from app.models.document import Document
from app.models.financial_fact import FinancialFact
from app.models.review import ReviewAction
from app.schemas.audit import AuditEventOut
from app.schemas.clarification import ClarificationOut
from app.schemas.conversation import TurnOut
from app.schemas.document import DocumentOut
from app.schemas.financial_fact import FinancialFactOut
from app.schemas.review import ReviewActionOut


def fact_display_value(fact: FinancialFact) -> str:
    if fact.measure_type in FINANCIAL_MEASURES:
        try:
            return format_inr(to_decimal(fact.normalized_value))
        except Exception:
            return fact.normalized_value
    if fact.field_key == "years_in_operation":
        return f"{fact.normalized_value} years"
    return fact.normalized_value


def fact_period_label(fact: FinancialFact) -> str | None:
    period = period_from_dates(fact.period_start, fact.period_end)
    return period.label if period else None


def fact_out(fact: FinancialFact) -> FinancialFactOut:
    definition = FACT_DEFINITIONS.get(fact.field_key)
    return FinancialFactOut(
        id=fact.id,
        application_id=fact.application_id,
        field_key=fact.field_key,
        label=fact.label or (definition.label if definition else fact.field_key),
        raw_value=fact.raw_value,
        normalized_value=fact.normalized_value,
        display_value=fact_display_value(fact),
        currency=fact.currency,
        period_start=fact.period_start,
        period_end=fact.period_end,
        period_label=fact_period_label(fact),
        measure_type=fact.measure_type,
        source_type=fact.source_type,
        source_document_id=fact.source_document_id,
        source_turn_id=fact.source_turn_id,
        source_locator=fact.source_locator,
        provenance_status=fact.provenance_status,
        extraction_method=fact.extraction_method,
        model_id=fact.model_id,
        prompt_version=fact.prompt_version,
        confidence_estimate=fact.confidence_estimate,
        version=fact.version,
        supersedes_id=fact.supersedes_id,
        notes=fact.notes,
        created_at=fact.created_at,
        updated_at=fact.updated_at,
    )


def document_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        application_id=document.application_id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        sha256=document.sha256,
        document_type=document.document_type,
        parser_profile=document.parser_profile,
        status=document.status,
        parse_notes=document.parse_notes,
        page_count=document.page_count,
        metadata_json=document.metadata_json or {},
        created_at=document.created_at,
    )


def turn_out(turn: ConversationTurn) -> TurnOut:
    return TurnOut(
        id=turn.id,
        application_id=turn.application_id,
        turn_index=turn.turn_index,
        speaker=turn.speaker,
        input_mode=turn.input_mode,
        transcript=turn.transcript,
        language=turn.language,
        intent=turn.intent,
        target_field=turn.target_field,
        question_id=turn.question_id,
        linked_fact_ids=turn.linked_fact_ids or [],
        provider_metadata=turn.provider_metadata or {},
        correction_status=turn.correction_status,
        created_at=turn.created_at,
    )


def clarification_out(clarification: Clarification) -> ClarificationOut:
    return ClarificationOut(
        id=clarification.id,
        application_id=clarification.application_id,
        field_key=clarification.field_key,
        question_text=clarification.question_text,
        reason=clarification.reason,
        expected_answer_type=clarification.expected_answer_type,
        status=clarification.status,
        priority=clarification.priority,
        source=clarification.source,
        language=clarification.language,
        created_at=clarification.created_at,
        answered_at=clarification.answered_at,
        answer_turn_id=clarification.answer_turn_id,
    )


def audit_out(event: AuditEvent) -> AuditEventOut:
    return AuditEventOut(
        id=event.id,
        application_id=event.application_id,
        actor=event.actor,
        event_type=event.event_type,
        summary=event.summary,
        detail_json=event.detail_json or {},
        created_at=event.created_at,
    )


def review_action_out(action: ReviewAction) -> ReviewActionOut:
    return ReviewActionOut(
        id=action.id,
        application_id=action.application_id,
        reviewer_name=action.reviewer_name,
        action=action.action,
        field_key=action.field_key,
        reason=action.reason,
        created_at=action.created_at,
    )
