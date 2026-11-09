from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationAppError
from app.domain.fact_definitions import resolve_field, target_field_payload
from app.domain.period import Period, period_from_dates
from app.domain.provenance import ExtractionMethod, ProvenanceStatus
from app.models.application import Application
from app.models.conversation_turn import ConversationTurn
from app.models.document import Document
from app.models.financial_fact import FinancialFact
from app.providers.interfaces import ReasoningProvider
from app.repositories.fact_repository import FactRepository
from app.services.evidence_service import EvidenceService, FactDraft

SOURCE_TYPE_BY_DOCUMENT = {
    "bank_statement": "bank_statement",
    "gst_summary": "GST_document",
    "gst_return": "GST_document",
    "gst_document": "GST_document",
    "sales_register": "sales_register",
    "other": "other_document",
}

APPLICANT_AMOUNT_FIELDS = {
    "annual_sales",
    "gst_turnover",
    "cash_sales",
    "sales_register_total",
    "bank_credits",
}


class ExtractionService:
    def __init__(self, db: Session, reasoning: ReasoningProvider) -> None:
        self.db = db
        self.reasoning = reasoning
        self.facts = FactRepository(db)
        self.evidence = EvidenceService(db)

    def extract_from_turn(
        self,
        application: Application,
        turn: ConversationTurn,
        target_field_keys: list[str],
        *,
        period_hint: Period | None = None,
    ) -> tuple[list[FinancialFact], list[str]]:
        prior_facts = [
            {
                "field_key": fact.field_key,
                "normalized_value": fact.normalized_value,
                "provenance_status": fact.provenance_status,
                "period_start": fact.period_start.isoformat() if fact.period_start else "",
                "period_end": fact.period_end.isoformat() if fact.period_end else "",
            }
            for fact in self.facts.list_for_application(application.id, include_rejected=False)
        ]
        result = self.reasoning.extract_applicant_facts(
            transcript=turn.transcript,
            target_fields=target_field_payload(target_field_keys),
            language=turn.language,
            prior_facts=prior_facts,
        )
        data = result.data
        candidates = data.get("candidate_facts") or []
        notes: list[str] = []
        allowed_fields = set(target_field_keys)
        created: list[FinancialFact] = []
        source_type = "applicant_speech" if turn.input_mode == "audio" else "applicant_text"
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            field_key = str(candidate.get("field_key", "")).strip()
            definition = resolve_field(field_key)
            if definition is None:
                notes.append(f"Ignored an unknown field from the model: {field_key}")
                continue
            if definition.field_key not in allowed_fields:
                notes.append(
                    f"Ignored a value for {definition.field_key} because it was not requested."
                )
                continue
            try:
                draft = self.evidence.build_draft(
                    field_key=definition.field_key,
                    raw_value=str(candidate.get("raw_value") or ""),
                    normalized_candidate=(
                        str(candidate.get("normalized_candidate"))
                        if candidate.get("normalized_candidate") is not None
                        else None
                    ),
                    currency=str(candidate.get("currency") or "INR"),
                    period_start=self._parse_date(candidate.get("period_start")),
                    period_end=self._parse_date(candidate.get("period_end")),
                    source_type=source_type,
                    provenance_status=ProvenanceStatus.CANDIDATE.value,
                    extraction_method=ExtractionMethod.MODEL_ASSISTED.value,
                    source_turn_id=turn.id,
                    source_locator=f"turn {turn.turn_index}",
                    model_id=result.model,
                    prompt_version=result.prompt_version,
                    confidence_estimate=self._confidence(candidate.get("confidence_estimate")),
                    notes=self._candidate_notes(candidate),
                    period_hint=period_hint,
                )
            except ValidationAppError as exc:
                notes.append(f"{definition.field_key}: {exc.message}")
                continue
            if self._duplicate_exists(application.id, draft):
                notes.append(f"{definition.field_key}: duplicate value ignored.")
                continue
            self._supersede_unconfirmed(application.id, draft, turn)
            fact = self.evidence.create_fact(application.id, draft)
            turn.linked_fact_ids = list(turn.linked_fact_ids or []) + [fact.id]
            created.append(fact)
        if data.get("unsupported_claims"):
            notes.extend(
                f"Model flagged an unsupported claim: {claim}"
                for claim in data.get("unsupported_claims", [])[:5]
            )
        self.evidence.record_batch_audit(
            application.id,
            actor=f"applicant:{application.id}",
            facts=created,
            source_label=f"conversation turn {turn.turn_index}",
        )
        return created, notes

    def extract_document_with_model(
        self,
        application: Application,
        document: Document,
        text: str,
        locators: list[dict[str, str]],
        target_field_keys: list[str],
    ) -> tuple[list[FinancialFact], list[str], str]:
        result = self.reasoning.extract_document_facts(
            text=text,
            document_type=document.document_type,
            source_locators=locators,
            target_fields=target_field_payload(target_field_keys),
        )
        data = result.data
        candidates = data.get("candidate_facts") or []
        notes = list(data.get("extraction_notes") or [])
        notes.extend(
            f"Unreadable section: {section}" for section in data.get("unreadable_sections", [])
        )
        source_type = SOURCE_TYPE_BY_DOCUMENT.get(document.document_type, "other_document")
        created: list[FinancialFact] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            field_key = str(candidate.get("field_key", "")).strip()
            definition = resolve_field(field_key)
            if definition is None:
                notes.append(f"Ignored an unknown document field: {field_key}")
                continue
            try:
                draft = self.evidence.build_draft(
                    field_key=definition.field_key,
                    raw_value=str(candidate.get("raw_value") or ""),
                    normalized_candidate=(
                        str(candidate.get("normalized_candidate"))
                        if candidate.get("normalized_candidate") is not None
                        else None
                    ),
                    currency=str(candidate.get("currency") or "INR"),
                    period_start=self._parse_date(candidate.get("period_start")),
                    period_end=self._parse_date(candidate.get("period_end")),
                    source_type=source_type,
                    provenance_status=ProvenanceStatus.DOCUMENT_EXTRACTED.value,
                    extraction_method=ExtractionMethod.MODEL_ASSISTED.value,
                    source_document_id=document.id,
                    source_locator=str(candidate.get("source_locator") or ""),
                    model_id=result.model,
                    prompt_version=result.prompt_version,
                    confidence_estimate=self._confidence(candidate.get("confidence_estimate")),
                    notes=str(candidate.get("notes") or "") or None,
                    measure_type_override=str(
                        candidate.get("measure_type") or definition.measure_type
                    ),
                    apply_default_period=False,
                )
            except ValidationAppError as exc:
                notes.append(f"{definition.field_key}: {exc.message}")
                continue
            if self._duplicate_exists(application.id, draft):
                notes.append(f"{definition.field_key}: duplicate value ignored.")
                continue
            fact = self.evidence.create_fact(application.id, draft)
            created.append(fact)
        self.evidence.record_batch_audit(
            application.id,
            actor=f"applicant:{application.id}",
            facts=created,
            source_label=f"document {document.original_filename}",
        )
        status = "parsed" if created else "parsed_with_warnings"
        return created, notes, status

    def _duplicate_exists(self, application_id: str, draft: FactDraft) -> bool:
        for fact in self.facts.list_for_application(application_id, include_rejected=False):
            if fact.field_key != draft.field_key:
                continue
            if fact.normalized_value != draft.normalized_value:
                continue
            existing_period = period_from_dates(fact.period_start, fact.period_end)
            draft_period = period_from_dates(draft.period_start, draft.period_end)
            if existing_period is None and draft_period is None:
                return True
            if (
                existing_period is not None
                and draft_period is not None
                and existing_period.same_as(draft_period)
            ):
                return True
        return False

    def _supersede_unconfirmed(
        self, application_id: str, draft: FactDraft, turn: ConversationTurn
    ) -> None:
        draft_period = period_from_dates(draft.period_start, draft.period_end)
        for fact in self.facts.list_for_application(application_id, include_rejected=False):
            if fact.field_key != draft.field_key:
                continue
            if fact.provenance_status != ProvenanceStatus.CANDIDATE.value:
                continue
            if fact.source_turn_id == turn.id:
                continue
            existing_period = period_from_dates(fact.period_start, fact.period_end)
            overlaps = (
                draft_period is None
                or existing_period is None
                or existing_period.overlaps(draft_period)
            )
            if not overlaps:
                continue
            fact.provenance_status = ProvenanceStatus.REJECTED.value
            fact.notes = (
                f"{fact.notes}; " if fact.notes else ""
            ) + "Superseded by a newer applicant statement. Prior value preserved in history."
            self.evidence.audit.record(
                application_id=application_id,
                actor=f"applicant:{application_id}",
                event_type="fact_superseded",
                summary=(
                    f"Prior unconfirmed {fact.field_key} value was superseded by a newer statement."
                ),
                detail={
                    "previous_fact_id": fact.id,
                    "field_key": fact.field_key,
                    "previous_value": fact.normalized_value,
                    "new_value": draft.normalized_value,
                    "turn_id": turn.id,
                },
            )

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if value is None or value == "":
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None

    @staticmethod
    def _confidence(value: object) -> float | None:
        try:
            if value is None:
                return None
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _candidate_notes(candidate: dict) -> str | None:
        parts = []
        if candidate.get("ambiguity_reason"):
            parts.append(str(candidate["ambiguity_reason"]))
        if candidate.get("evidence_quote"):
            parts.append(f"Evidence: {candidate['evidence_quote']}")
        return "; ".join(parts) or None


def document_target_fields(document_type: str) -> list[str]:
    if document_type == "bank_statement":
        return ["bank_credits"]
    if document_type in {"gst_summary", "gst_return", "gst_document"}:
        return ["gst_turnover"]
    if document_type == "sales_register":
        return ["cash_sales", "sales_register_total"]
    return ["annual_sales", "gst_turnover", "bank_credits", "cash_sales"]
