from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_CURRENCY
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.domain.fact_definitions import FactDefinition, resolve_field
from app.domain.money import (
    decimal_to_string,
    format_inr,
    quantize_money,
    to_decimal,
    validate_currency,
)
from app.domain.number_normalizer import normalize_amount
from app.domain.period import Period, period_from_dates, previous_fy_period
from app.domain.provenance import (
    ExtractionMethod,
    ProvenanceStatus,
    can_transition_fact,
)
from app.models.financial_fact import FinancialFact
from app.repositories.fact_repository import FactRepository
from app.schemas.financial_fact import FactCorrectionRequest, FactCorrectionResponse
from app.services.audit_service import AuditService
from app.services.serializers import fact_out

AMOUNT_FIELDS = {
    "annual_sales",
    "gst_turnover",
    "cash_sales",
    "sales_register_total",
    "bank_credits",
}

APPLICANT_ENTERABLE_FIELDS = frozenset(
    {
        "business_type",
        "years_in_operation",
        "annual_sales",
        "gst_turnover",
        "cash_sales",
        "sales_register_total",
    }
)


@dataclass
class FactDraft:
    field_key: str
    raw_value: str
    normalized_value: str
    currency: str
    measure_type: str
    source_type: str
    provenance_status: str
    extraction_method: str
    period_start: date | None = None
    period_end: date | None = None
    source_document_id: str | None = None
    source_turn_id: str | None = None
    source_locator: str | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    confidence_estimate: float | None = None
    notes: str | None = None
    label: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class FactBatchResult:
    facts: list[FinancialFact]
    notes: list[str]


class EvidenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.facts = FactRepository(db)
        self.audit = AuditService(db)

    def build_draft(
        self,
        *,
        field_key: str,
        raw_value: str,
        normalized_candidate: str | None,
        currency: str,
        period_start: date | None,
        period_end: date | None,
        source_type: str,
        provenance_status: str,
        extraction_method: str,
        source_document_id: str | None = None,
        source_turn_id: str | None = None,
        source_locator: str | None = None,
        model_id: str | None = None,
        prompt_version: str | None = None,
        confidence_estimate: float | None = None,
        notes: str | None = None,
        period_hint: Period | None = None,
        measure_type_override: str | None = None,
        apply_default_period: bool = True,
    ) -> FactDraft:
        definition = resolve_field(field_key)
        if definition is None:
            raise ValidationAppError(f"Unknown financial fact field: {field_key}")
        normalized_value = self._normalize_value(
            definition, normalized_candidate or raw_value, raw_value
        )
        parsed_start, parsed_end, period_notes = self._normalize_period(period_start, period_end)
        applied_hint = False
        if (
            apply_default_period
            and parsed_start is None
            and parsed_end is None
            and definition.default_period
        ):
            hint = period_hint or previous_fy_period()
            parsed_start, parsed_end = hint.start, hint.end
            applied_hint = True
        combined_notes = "; ".join(part for part in (notes, period_notes) if part) or None
        if applied_hint:
            combined_notes = "; ".join(
                part
                for part in (
                    combined_notes,
                    "Period applied from the question context; the applicant did not state a "
                    "different period.",
                )
                if part
            )
        return FactDraft(
            field_key=definition.field_key,
            raw_value=raw_value.strip() or normalized_value,
            normalized_value=normalized_value,
            currency=validate_currency(currency),
            measure_type=measure_type_override or definition.measure_type,
            source_type=source_type or definition.source_type,
            provenance_status=provenance_status,
            extraction_method=extraction_method,
            period_start=parsed_start,
            period_end=parsed_end,
            source_document_id=source_document_id,
            source_turn_id=source_turn_id,
            source_locator=source_locator,
            model_id=model_id,
            prompt_version=prompt_version,
            confidence_estimate=confidence_estimate,
            notes=combined_notes,
            label=definition.label,
        )

    def create_fact(self, application_id: str, draft: FactDraft) -> FinancialFact:
        fact = FinancialFact(
            application_id=application_id,
            field_key=draft.field_key,
            label=draft.label or draft.field_key,
            raw_value=draft.raw_value[:255],
            normalized_value=draft.normalized_value[:64],
            currency=draft.currency,
            period_start=draft.period_start,
            period_end=draft.period_end,
            measure_type=draft.measure_type,
            source_type=draft.source_type,
            source_document_id=draft.source_document_id,
            source_turn_id=draft.source_turn_id,
            source_locator=draft.source_locator,
            provenance_status=draft.provenance_status,
            extraction_method=draft.extraction_method,
            model_id=draft.model_id,
            prompt_version=draft.prompt_version,
            confidence_estimate=draft.confidence_estimate,
            version=self._next_version(application_id, draft.field_key),
            notes=draft.notes,
        )
        return self.facts.add(fact)

    def record_batch_audit(
        self,
        application_id: str,
        actor: str,
        facts: list[FinancialFact],
        *,
        source_label: str,
    ) -> None:
        if not facts:
            return
        self.audit.record(
            application_id=application_id,
            actor=actor,
            event_type="facts_extracted",
            summary=f"{len(facts)} candidate fact(s) recorded from {source_label}.",
            detail={
                "fact_ids": [fact.id for fact in facts],
                "field_keys": sorted({fact.field_key for fact in facts}),
                "provenance_statuses": sorted({fact.provenance_status for fact in facts}),
            },
        )

    def confirm(self, fact: FinancialFact, actor: str) -> FactCorrectionResponse:
        if fact.provenance_status == ProvenanceStatus.REJECTED.value:
            raise ConflictError("A rejected fact cannot be confirmed")
        if fact.provenance_status == ProvenanceStatus.REVIEWER_VERIFIED.value:
            raise ConflictError("This fact has already been verified by a reviewer")
        if not can_transition_fact(fact.provenance_status, ProvenanceStatus.APPLICANT_CONFIRMED):
            raise ConflictError("This fact cannot be confirmed in its current state")
        previous_status = fact.provenance_status
        fact.provenance_status = ProvenanceStatus.APPLICANT_CONFIRMED.value
        fact.notes = self._append_note(fact.notes, "Applicant confirmed this value.")
        self.audit.record(
            application_id=fact.application_id,
            actor=actor,
            event_type="fact_confirmed",
            summary=f"Applicant confirmed {fact.field_key}.",
            detail={
                "fact_id": fact.id,
                "field_key": fact.field_key,
                "previous_status": previous_status,
                "new_status": fact.provenance_status,
            },
        )
        self.db.commit()
        return FactCorrectionResponse(
            fact=fact_out(fact),
            previous_fact_id=None,
            message="Value confirmed. The original evidence is preserved.",
        )

    def declare_applicant_fact(
        self,
        application_id: str,
        *,
        field_key: str,
        value: str,
        period_start: date | None,
        period_end: date | None,
        actor: str,
    ) -> FactCorrectionResponse:
        definition = resolve_field(field_key)
        if definition is None or definition.field_key not in APPLICANT_ENTERABLE_FIELDS:
            raise ValidationAppError("This field cannot be entered directly by the applicant")
        existing = self.facts.latest_for_field(application_id, definition.field_key)
        if (
            existing is not None
            and existing.provenance_status == ProvenanceStatus.REVIEWER_VERIFIED.value
        ):
            raise ConflictError("A reviewer-verified value cannot be replaced by the applicant")
        draft = self.build_draft(
            field_key=definition.field_key,
            raw_value=value,
            normalized_candidate=value,
            currency=DEFAULT_CURRENCY,
            period_start=period_start,
            period_end=period_end,
            source_type="applicant_text",
            provenance_status=ProvenanceStatus.APPLICANT_CONFIRMED.value,
            extraction_method=ExtractionMethod.APPLICANT_ENTERED.value,
            confidence_estimate=1.0,
            notes="Applicant entered this value directly.",
        )
        fact = self.create_fact(application_id, draft)
        if existing is not None:
            existing.provenance_status = ProvenanceStatus.REJECTED.value
            existing.notes = self._append_note(
                existing.notes, f"Superseded by applicant entry {fact.id}."
            )
        self.audit.record(
            application_id=application_id,
            actor=actor,
            event_type="fact_declared",
            summary=f"Applicant entered {definition.field_key} directly.",
            detail={
                "fact_id": fact.id,
                "field_key": definition.field_key,
                "previous_fact_id": existing.id if existing is not None else None,
            },
        )
        self.db.commit()
        return FactCorrectionResponse(
            fact=fact_out(fact),
            previous_fact_id=existing.id if existing is not None else None,
            message="Value saved and confirmed. The prior value remains in history.",
        )

    def correct(
        self, fact: FinancialFact, payload: FactCorrectionRequest, actor: str
    ) -> FactCorrectionResponse:
        if fact.provenance_status == ProvenanceStatus.REJECTED.value:
            raise ConflictError("A rejected fact cannot be corrected; add a new value instead")
        if fact.provenance_status == ProvenanceStatus.REVIEWER_VERIFIED.value:
            raise ConflictError("A reviewer-verified fact cannot be changed by the applicant")
        if not can_transition_fact(fact.provenance_status, ProvenanceStatus.REJECTED):
            raise ConflictError("This fact cannot be corrected in its current state")
        definition = resolve_field(fact.field_key)
        if definition is None:
            raise ConflictError("This fact cannot be corrected through the applicant flow")
        normalized = self._normalize_value(
            definition,
            payload.normalized_value or "",
            payload.raw_value or payload.normalized_value or "",
        )
        start = payload.period_start if payload.period_start is not None else fact.period_start
        end = payload.period_end if payload.period_end is not None else fact.period_end
        parsed_start, parsed_end, _ = self._normalize_period(start, end)
        new_fact = FinancialFact(
            application_id=fact.application_id,
            field_key=fact.field_key,
            label=fact.label,
            raw_value=(payload.raw_value or payload.normalized_value or normalized)[:255],
            normalized_value=normalized[:64],
            currency=fact.currency,
            period_start=parsed_start,
            period_end=parsed_end,
            measure_type=fact.measure_type,
            source_type=fact.source_type,
            source_document_id=fact.source_document_id,
            source_turn_id=fact.source_turn_id,
            source_locator=fact.source_locator,
            provenance_status=ProvenanceStatus.APPLICANT_CONFIRMED.value,
            extraction_method=ExtractionMethod.APPLICANT_ENTERED.value,
            model_id=None,
            prompt_version=None,
            confidence_estimate=1.0,
            version=fact.version + 1,
            supersedes_id=fact.id,
            notes=payload.notes
            or "Applicant correction. The superseded value and original evidence are preserved.",
        )
        self.facts.add(new_fact)
        fact.provenance_status = ProvenanceStatus.REJECTED.value
        fact.notes = self._append_note(
            fact.notes, f"Superseded by applicant correction {new_fact.id}."
        )
        self.audit.record(
            application_id=fact.application_id,
            actor=actor,
            event_type="fact_corrected",
            summary=f"Applicant corrected {fact.field_key}; the prior value was preserved.",
            detail={
                "previous_fact_id": fact.id,
                "new_fact_id": new_fact.id,
                "field_key": fact.field_key,
                "previous_value": fact.normalized_value,
                "new_value": new_fact.normalized_value,
            },
        )
        self.db.commit()
        return FactCorrectionResponse(
            fact=fact_out(new_fact),
            previous_fact_id=fact.id,
            message="Correction saved as a new version. The prior value remains in history.",
        )

    def reject(self, fact: FinancialFact, reason: str, actor: str) -> FactCorrectionResponse:
        if fact.provenance_status == ProvenanceStatus.REJECTED.value:
            raise ConflictError("This fact is already rejected")
        if fact.provenance_status == ProvenanceStatus.REVIEWER_VERIFIED.value:
            raise ConflictError("A reviewer-verified fact cannot be rejected by the applicant")
        if not can_transition_fact(fact.provenance_status, ProvenanceStatus.REJECTED):
            raise ConflictError("This fact cannot be rejected in its current state")
        fact.provenance_status = ProvenanceStatus.REJECTED.value
        fact.notes = self._append_note(fact.notes, f"Rejected: {reason}")
        self.audit.record(
            application_id=fact.application_id,
            actor=actor,
            event_type="fact_rejected",
            summary=f"Applicant rejected {fact.field_key}.",
            detail={"fact_id": fact.id, "field_key": fact.field_key, "reason": reason},
        )
        self.db.commit()
        return FactCorrectionResponse(
            fact=fact_out(fact),
            previous_fact_id=None,
            message="Value rejected. It remains in history with the reason recorded.",
        )

    def reviewer_verify(self, fact: FinancialFact, actor: str, reason: str) -> FinancialFact:
        if fact.provenance_status == ProvenanceStatus.REJECTED.value:
            raise ConflictError("A rejected fact cannot be verified")
        if fact.provenance_status == ProvenanceStatus.REVIEWER_VERIFIED.value:
            return fact
        if not can_transition_fact(fact.provenance_status, ProvenanceStatus.REVIEWER_VERIFIED):
            raise ConflictError("This fact cannot be verified in its current state")
        previous_status = fact.provenance_status
        fact.provenance_status = ProvenanceStatus.REVIEWER_VERIFIED.value
        fact.notes = self._append_note(fact.notes, f"Reviewer verified: {reason}")
        self.audit.record(
            application_id=fact.application_id,
            actor=actor,
            event_type="fact_verified",
            summary=f"Reviewer verified {fact.field_key}.",
            detail={
                "fact_id": fact.id,
                "field_key": fact.field_key,
                "previous_status": previous_status,
                "reason": reason,
            },
        )
        return fact

    def reviewer_reject(self, fact: FinancialFact, actor: str, reason: str) -> FinancialFact:
        if fact.provenance_status == ProvenanceStatus.REJECTED.value:
            return fact
        if fact.provenance_status == ProvenanceStatus.REVIEWER_VERIFIED.value:
            raise ConflictError("A reviewer-verified fact cannot be rejected")
        if not can_transition_fact(fact.provenance_status, ProvenanceStatus.REJECTED):
            raise ConflictError("This fact cannot be rejected in its current state")
        fact.provenance_status = ProvenanceStatus.REJECTED.value
        fact.notes = self._append_note(fact.notes, f"Reviewer rejected: {reason}")
        self.audit.record(
            application_id=fact.application_id,
            actor=actor,
            event_type="fact_rejected_by_reviewer",
            summary=f"Reviewer rejected {fact.field_key}.",
            detail={"fact_id": fact.id, "field_key": fact.field_key, "reason": reason},
        )
        return fact

    def get_fact(self, fact_id: str) -> FinancialFact:
        fact = self.facts.get(fact_id)
        if fact is None:
            raise NotFoundError("Financial fact not found")
        return fact

    def _next_version(self, application_id: str, field_key: str) -> int:
        existing = self.facts.list_for_application(application_id)
        versions = [fact.version for fact in existing if fact.field_key == field_key]
        return max(versions, default=0) + 1

    def _normalize_value(self, definition: FactDefinition, candidate: str, raw_value: str) -> str:
        text = (candidate or "").strip()
        if definition.value_type == "amount":
            amount = normalize_amount(text)
            if amount is None and raw_value.strip() != text:
                amount = normalize_amount(raw_value)
            if amount is None:
                raise ValidationAppError(f"Could not parse an amount for {definition.field_key}")
            if amount < 0:
                raise ValidationAppError("Negative financial amounts are not accepted")
            return decimal_to_string(quantize_money(amount))
        if definition.value_type == "number":
            match = re.search(r"\d+(?:\.\d+)?", text)
            if match is None:
                raise ValidationAppError(f"Could not parse a number for {definition.field_key}")
            return match.group(0)
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            raise ValidationAppError(f"Value for {definition.field_key} is empty")
        return cleaned[:255]

    def _normalize_period(
        self, start: date | None, end: date | None
    ) -> tuple[date | None, date | None, str | None]:
        if start is None and end is None:
            return None, None, None
        if start is None or end is None:
            return (
                None,
                None,
                "Only one period boundary was provided, so the value is unperiodized.",
            )
        if end < start:
            raise ValidationAppError("Period end cannot be before period start")
        period_from_dates(start, end)
        return start, end, None

    @staticmethod
    def _append_note(existing: str | None, note: str) -> str:
        if not existing:
            return note
        return f"{existing}; {note}"

    @staticmethod
    def format_amount(value: Decimal | str) -> str:
        return format_inr(to_decimal(value))


def amount_display(value: str) -> str:
    try:
        return format_inr(to_decimal(value))
    except Exception:
        return value
