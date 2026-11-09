from __future__ import annotations

from pydantic import BaseModel


class ComparisonOut(BaseModel):
    status: str
    left_field: str
    right_field: str
    left_label: str
    right_label: str
    left_value: str | None
    right_value: str | None
    difference: str | None
    percent_difference: str | None
    tolerance_percent: str | None
    period_label: str | None
    explanation: str
    requires_clarification: bool
    clarification_field: str | None
    clarification_reason: str | None
    evidence_ids: list[str]


class ReconciliationOut(BaseModel):
    tolerance_percent: str
    policy_note: str
    comparisons: list[ComparisonOut]
    status_counts: dict[str, int]
    missing_required_fields: list[str]
    has_blocking_difference: bool
    fact_count: int
    selected_fact_ids: dict[str, str]
