from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.application import ApplicationOut, CompletenessOut
from app.schemas.audit import AuditEventOut
from app.schemas.clarification import ClarificationOut
from app.schemas.conversation import TurnOut
from app.schemas.document import DocumentOut
from app.schemas.financial_fact import FinancialFactOut
from app.schemas.reconciliation import ReconciliationOut

REVIEW_ACTIONS = ("verify_fact", "reject_fact", "request_information", "complete_review")


class ReviewerQueueItem(BaseModel):
    application_id: str
    reference: str
    applicant_name: str
    business_name: str
    status: str
    submitted_at: datetime | None
    created_at: datetime
    open_clarifications: int
    completeness_percent: int
    is_demo: bool


class ReviewQueueOut(BaseModel):
    items: list[ReviewerQueueItem]
    total: int


class ReviewActionRequest(BaseModel):
    action: Literal["verify_fact", "reject_fact", "request_information", "complete_review"]
    field_key: str | None = Field(default=None, max_length=80)
    reason: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def require_field_for_fact_action(self) -> ReviewActionRequest:
        if self.action in {"verify_fact", "reject_fact"} and not self.field_key:
            raise ValueError("field_key is required for fact verification actions")
        return self


class ReviewActionOut(BaseModel):
    id: str
    application_id: str
    reviewer_name: str
    action: str
    field_key: str | None
    reason: str
    created_at: datetime


class ReviewerSummaryOut(BaseModel):
    source: str
    prompt_version: str | None
    applicant_declared_facts: list[str]
    document_derived_facts: list[str]
    applicant_explanations: list[str]
    unresolved_items: list[str]
    limitations: list[str]
    source_references: list[str]


class ReviewerApplicationOut(BaseModel):
    application: ApplicationOut
    completeness: CompletenessOut
    facts: list[FinancialFactOut]
    documents: list[DocumentOut]
    turns: list[TurnOut]
    clarifications: list[ClarificationOut]
    reconciliation: ReconciliationOut
    audit_events: list[AuditEventOut]
    review_actions: list[ReviewActionOut]
    summary: ReviewerSummaryOut
    boundary_notice: str
