from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.exceptions import InvalidStateTransition
from app.core.lifecycle import (
    ApplicationStatus,
    assert_transition,
    can_transition,
)
from app.domain.financial_rules import (
    ComparisonStatus,
    FactSnapshot,
    ReconciliationPolicy,
    reconcile,
)
from app.domain.number_normalizer import find_amounts, normalize_amount
from app.domain.period import fy_period, parse_period
from app.domain.provenance import ProvenanceStatus


def snapshot(field_key: str, measure_type: str, value: str) -> FactSnapshot:
    return FactSnapshot(
        id=f"fact-{field_key}",
        field_key=field_key,
        label=field_key,
        measure_type=measure_type,
        normalized_value=value,
        raw_value=value,
        currency="INR",
        period=fy_period(2025),
        source_type="applicant_text",
        provenance_status=ProvenanceStatus.APPLICANT_CONFIRMED.value,
    )


def test_amount_normalization_handles_indian_and_composite_scales():
    assert normalize_amount("18 lakh") == Decimal("1800000")
    assert normalize_amount("16 lakh 50 thousand") == Decimal("1650000")
    assert normalize_amount("1.2 crore") == Decimal("12000000")
    assert normalize_amount("Rs. 18,00,000") == Decimal("1800000")
    assert normalize_amount("not an amount") is None


def test_find_amounts_does_not_duplicate_numeric_and_word_matches():
    found = find_amounts("sales were 18 lakh and GST was 16 lakh 50 thousand")
    values = [value for _, value in found]
    assert set(values) == {Decimal("1800000"), Decimal("1650000")}
    assert len(values) == 2


def test_period_parsing_uses_indian_financial_year():
    period = parse_period("FY2025-26")
    assert period is not None
    assert period.start.isoformat() == "2025-04-01"
    assert period.end.isoformat() == "2026-03-31"
    assert period.label == "FY2025-26"


def test_reconciliation_aliases_and_measure_caveats():
    facts = [
        snapshot("annual_sales", "declared_sales", "1800000"),
        snapshot("gst_turnover", "gst_turnover", "1650000"),
        snapshot("bank_credits", "bank_credit", "3400000"),
    ]
    result = reconcile(facts, ReconciliationPolicy())
    assert result["missing_required_fields"] == []
    assert result["has_blocking_difference"] is True
    statuses = {item["status"] for item in result["comparisons"]}
    assert ComparisonStatus.DIFFERENCE_REQUIRES_CONTEXT.value in statuses
    assert ComparisonStatus.NOT_COMPARABLE_MEASURE.value in statuses
    assert any(
        "Bank credits are not revenue" in item["explanation"] for item in result["comparisons"]
    )


def test_reconciliation_reports_missing_information_without_zero_filling():
    result = reconcile(
        [snapshot("annual_sales", "declared_sales", "1800000")],
        ReconciliationPolicy(),
    )
    assert set(result["missing_required_fields"]) == {"gst_turnover", "bank_credit"}
    assert any(
        item["status"] == ComparisonStatus.MISSING_INFORMATION.value
        for item in result["comparisons"]
    )


def test_lifecycle_requires_human_review_before_completion():
    assert can_transition(
        ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
        ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS,
    )
    assert not can_transition(
        ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
        ApplicationStatus.REVIEW_COMPLETED,
    )
    with pytest.raises(InvalidStateTransition):
        assert_transition(
            ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
            ApplicationStatus.REVIEW_COMPLETED,
        )
