from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FinancialFactOut(BaseModel):
    id: str
    application_id: str
    field_key: str
    label: str
    raw_value: str
    normalized_value: str
    display_value: str
    currency: str
    period_start: date | None
    period_end: date | None
    period_label: str | None
    measure_type: str
    source_type: str
    source_document_id: str | None
    source_turn_id: str | None
    source_locator: str | None
    provenance_status: str
    extraction_method: str
    model_id: str | None
    prompt_version: str | None
    confidence_estimate: float | None
    version: int
    supersedes_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class FinancialFactListOut(BaseModel):
    items: list[FinancialFactOut]


class FactCorrectionRequest(BaseModel):
    action: Literal["confirm", "correct", "reject"]
    normalized_value: str | None = Field(default=None, max_length=64)
    raw_value: str | None = Field(default=None, max_length=255)
    period_start: date | None = None
    period_end: date | None = None
    notes: str | None = Field(default=None, max_length=1000)
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_value_for_correction(self) -> FactCorrectionRequest:
        if self.action == "correct" and not self.normalized_value:
            raise ValueError("A corrected normalized_value is required")
        if self.action == "reject" and not self.reason:
            raise ValueError("A reason is required when rejecting a fact")
        return self


class ApplicantFactCreate(BaseModel):
    field_key: Literal[
        "business_type",
        "years_in_operation",
        "annual_sales",
        "gst_turnover",
        "cash_sales",
        "sales_register_total",
    ]
    value: str = Field(min_length=1, max_length=255)
    period_start: date | None = None
    period_end: date | None = None


class FactCorrectionResponse(BaseModel):
    fact: FinancialFactOut
    previous_fact_id: str | None
    message: str
