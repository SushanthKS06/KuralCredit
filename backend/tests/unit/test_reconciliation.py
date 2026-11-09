from __future__ import annotations

from app.domain.financial_rules import (
    ComparisonStatus,
    FactSnapshot,
    ReconciliationPolicy,
    reconcile,
)
from app.domain.period import fy_period


def test_reconciliation_bank_credits_are_not_revenue():
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
            field_key="bank_credits",
            label="Bank Statement Credits",
            measure_type="bank_credit",
            normalized_value="3400000",
            raw_value="34 lakh",
            currency="INR",
            period=fy_period(2025),
            source_type="bank_statement",
            provenance_status="document_extracted",
        ),
    ]

    policy = ReconciliationPolicy()
    result = reconcile(facts, policy)

    comparisons = result.get("comparisons")
    assert isinstance(comparisons, list)

    # Must NOT conclude fraud
    assert not any(
        "fraud" in str(c.get("status", "")).lower() for c in comparisons if isinstance(c, dict)
    )

    # Must flag non-comparable measure and state that bank credits are not revenue
    target_status = ComparisonStatus.NOT_COMPARABLE_MEASURE.value
    non_comp = [c for c in comparisons if isinstance(c, dict) and c.get("status") == target_status]
    assert len(non_comp) >= 1
    assert "bank credits are not revenue" in str(non_comp[0].get("explanation", "")).lower()
