from __future__ import annotations

from app.domain.financial_rules import (
    ComparisonStatus,
    FactSnapshot,
    ReconciliationPolicy,
    reconcile,
)
from app.domain.period import fy_period


def test_clarification_neutral_framing():
    facts = [
        FactSnapshot(
            id="f1",
            field_key="annual_sales",
            label="Annual Sales",
            measure_type="declared_sales",
            normalized_value="1800000",
            raw_value="18 lakh",
            currency="INR",
            period=fy_period(2025),
            source_type="applicant_text",
            provenance_status="applicant_confirmed",
        ),
        FactSnapshot(
            id="f2",
            field_key="gst_turnover",
            label="GST Turnover",
            measure_type="gst_turnover",
            normalized_value="1650000",
            raw_value="16.5 lakh",
            currency="INR",
            period=fy_period(2025),
            source_type="gst_document",
            provenance_status="document_extracted",
        ),
    ]

    # pyrefly: ignore[bad-argument-type]
    policy = ReconciliationPolicy(tolerance_percent=5)
    result = reconcile(facts, policy)

    # 18L vs 16.5L has an 8.33% difference (> 5% tolerance)
    assert result["has_blocking_difference"] is True
    comparisons = result.get("comparisons")
    assert isinstance(comparisons, list)
    target_status = ComparisonStatus.DIFFERENCE_REQUIRES_CONTEXT.value
    diff_comp = [c for c in comparisons if isinstance(c, dict) and c.get("status") == target_status]
    assert len(diff_comp) == 1
    # Check that explanation is neutral and does NOT call it fraud
    explanation = str(diff_comp[0].get("explanation", "")).lower()
    assert "fraud" not in explanation
    assert "difference" in explanation
