from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.financial_rules import (
    FactSnapshot,
    ReconciliationPolicy,
    reconcile,
)
from app.domain.money import to_decimal
from app.domain.period import period_from_dates
from app.models.application import Application
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.fact_repository import FactRepository
from app.schemas.reconciliation import ReconciliationOut
from app.services.serializers import fact_display_value


class ReconciliationService:
    def __init__(self, db: Session, tolerance_percent) -> None:
        self.db = db
        self.facts = FactRepository(db)
        self.conversations = ConversationRepository(db)
        self.policy = ReconciliationPolicy(tolerance_percent=tolerance_percent)

    def build(self, application: Application) -> dict[str, object]:
        facts = self.facts.list_for_application(application.id, include_rejected=False)
        snapshots: list[FactSnapshot] = []
        for fact in facts:
            if fact.measure_type not in {
                "declared_sales",
                "gst_turnover",
                "bank_credit",
                "cash_sales",
                "sales_register_total",
            }:
                continue
            try:
                to_decimal(fact.normalized_value)
            except Exception:
                continue
            snapshots.append(
                FactSnapshot(
                    id=fact.id,
                    field_key=fact.field_key,
                    label=fact.label,
                    measure_type=fact.measure_type,
                    normalized_value=fact.normalized_value,
                    raw_value=fact.raw_value,
                    currency=fact.currency,
                    period=period_from_dates(fact.period_start, fact.period_end),
                    source_type=fact.source_type,
                    provenance_status=fact.provenance_status,
                    source_document_id=fact.source_document_id,
                    source_turn_id=fact.source_turn_id,
                    source_locator=fact.source_locator,
                    version=fact.version,
                    notes=fact.notes,
                )
            )
        answered = self.conversations.list_clarifications(application.id, status="answered")
        explanation_fields = {clarification.field_key for clarification in answered}
        return reconcile(snapshots, self.policy, explanation_fields=explanation_fields)

    def out(self, application: Application) -> ReconciliationOut:
        return ReconciliationOut.model_validate(self.build(application))

    def context_fact_payload(self, application: Application) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for fact in self.facts.list_for_application(application.id, include_rejected=False):
            payload.append(
                {
                    "field_key": fact.field_key,
                    "label": fact.label,
                    "display_value": fact_display_value(fact),
                    "provenance_status": fact.provenance_status,
                    "period": (
                        period_from_dates(fact.period_start, fact.period_end).label
                        if period_from_dates(fact.period_start, fact.period_end)
                        else ""
                    ),
                }
            )
        return payload
