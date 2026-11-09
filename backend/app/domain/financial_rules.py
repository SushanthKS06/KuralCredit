from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from app.domain.money import is_within_tolerance, percentage_difference, to_decimal
from app.domain.period import Period, periods_comparable
from app.domain.provenance import PROVENANCE_PRIORITY, ProvenanceStatus


class ComparisonStatus(StrEnum):
    WITHIN_TOLERANCE = "within_tolerance"
    DIFFERENCE_REQUIRES_CONTEXT = "difference_requires_context"
    CONTEXT_PROVIDED = "context_provided"
    NOT_COMPARABLE_MEASURE = "not_comparable_measure"
    NOT_COMPARABLE_PERIOD = "not_comparable_period"
    MISSING_INFORMATION = "missing_information"
    DUPLICATE_OVERLAP = "duplicate_overlap"


MEASURE_LABELS = {
    "declared_sales": "Applicant-declared annual sales",
    "gst_turnover": "GST-reported turnover",
    "bank_credit": "Bank statement credits",
    "cash_sales": "Cash sales",
    "sales_register_total": "Sales register total",
}

COMPARABLE_MEASURE_PAIRS = frozenset(
    {
        frozenset({"declared_sales", "gst_turnover"}),
    }
)

NON_COMPARABLE_MEASURE_PAIRS = frozenset(
    {
        frozenset({"declared_sales", "bank_credit"}),
        frozenset({"gst_turnover", "bank_credit"}),
        frozenset({"cash_sales", "bank_credit"}),
    }
)

MEASURE_CAVEATS = {
    frozenset({"declared_sales", "gst_turnover"}): (
        "Declared sales and GST turnover are related but not identical. GST turnover may exclude "
        "exempt or composition supplies, and timing of invoices can differ."
    ),
    frozenset({"declared_sales", "bank_credit"}): (
        "Bank credits are not revenue. They can include customer receipts, transfers between own "
        "accounts, loan disbursements, refunds, deposits, and non-business credits."
    ),
    frozenset({"gst_turnover", "bank_credit"}): (
        "GST turnover and bank deposits measure different things. Bank credits can include "
        "non-sales inflows, and GST turnover can include credit sales not yet collected."
    ),
    frozenset({"cash_sales", "bank_credit"}): (
        "Cash sales may never pass through the bank account. Bank credits are not a proxy for "
        "sales."
    ),
}


@dataclass(frozen=True)
class ReconciliationPolicy:
    tolerance_percent: Decimal = Decimal("5")
    required_fields: tuple[str, ...] = ("declared_sales", "gst_turnover", "bank_credit")
    ask_for_context_on_measure_mismatch: bool = True


@dataclass(frozen=True)
class FactSnapshot:
    id: str
    field_key: str
    label: str
    measure_type: str
    normalized_value: str
    raw_value: str
    currency: str
    period: Period | None
    source_type: str
    provenance_status: str
    source_document_id: str | None = None
    source_turn_id: str | None = None
    source_locator: str | None = None
    version: int = 1
    notes: str | None = None

    @property
    def value(self) -> Decimal:
        return to_decimal(self.normalized_value)

    @property
    def priority(self) -> int:
        return PROVENANCE_PRIORITY.get(ProvenanceStatus(self.provenance_status), 0)


@dataclass
class ComparisonResult:
    status: ComparisonStatus
    left_field: str
    right_field: str
    left_label: str
    right_label: str
    left_value: str | None = None
    right_value: str | None = None
    difference: str | None = None
    percent_difference: str | None = None
    tolerance_percent: str | None = None
    period_label: str | None = None
    explanation: str = ""
    requires_clarification: bool = False
    clarification_field: str | None = None
    clarification_reason: str | None = None
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "left_field": self.left_field,
            "right_field": self.right_field,
            "left_label": self.left_label,
            "right_label": self.right_label,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "difference": self.difference,
            "percent_difference": self.percent_difference,
            "tolerance_percent": self.tolerance_percent,
            "period_label": self.period_label,
            "explanation": self.explanation,
            "requires_clarification": self.requires_clarification,
            "clarification_field": self.clarification_field,
            "clarification_reason": self.clarification_reason,
            "evidence_ids": self.evidence_ids,
        }


def select_primary_facts(facts: list[FactSnapshot]) -> dict[str, FactSnapshot]:
    selected: dict[str, FactSnapshot] = {}
    for fact in facts:
        if fact.provenance_status == ProvenanceStatus.REJECTED.value:
            continue
        current = selected.get(fact.field_key)
        if current is None:
            selected[fact.field_key] = fact
            continue
        current_period = current.period
        fact_period = fact.period
        if fact_period and current_period and not fact_period.same_as(current_period):
            continue
        if fact.priority > current.priority or (
            fact.priority == current.priority and fact.version > current.version
        ):
            selected[fact.field_key] = fact
    return selected


def detect_duplicate_overlaps(facts: list[FactSnapshot]) -> list[ComparisonResult]:
    results: list[ComparisonResult] = []
    active = [
        fact
        for fact in facts
        if fact.provenance_status != ProvenanceStatus.REJECTED.value and fact.period is not None
    ]
    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if left.field_key != right.field_key:
                continue
            if left.period is None or right.period is None:
                continue
            if not left.period.overlaps(right.period):
                continue
            if left.value == right.value:
                continue
            results.append(
                ComparisonResult(
                    status=ComparisonStatus.DUPLICATE_OVERLAP,
                    left_field=left.field_key,
                    right_field=right.field_key,
                    left_label=left.label,
                    right_label=right.label,
                    left_value=str(left.value),
                    right_value=str(right.value),
                    period_label=left.period.label,
                    explanation=(
                        "Two active records for the same measure cover overlapping periods with "
                        "different values. Reviewers should confirm which record applies."
                    ),
                    requires_clarification=False,
                    evidence_ids=[left.id, right.id],
                )
            )
    return results


def compare_facts(
    left: FactSnapshot | None,
    right: FactSnapshot | None,
    policy: ReconciliationPolicy,
    *,
    explanation_present: bool = False,
) -> ComparisonResult:
    left_field = left.field_key if left else "missing_left"
    right_field = right.field_key if right else "missing_right"
    left_label = left.label if left else left_field
    right_label = right.label if right else right_field
    if left is None or right is None:
        missing = left_field if left is None else right_field
        return ComparisonResult(
            status=ComparisonStatus.MISSING_INFORMATION,
            left_field=left_field,
            right_field=right_field,
            left_label=left_label,
            right_label=right_label,
            left_value=str(left.value) if left else None,
            right_value=str(right.value) if right else None,
            explanation=f"Missing information for {missing}. Missing data is not treated as zero.",
            requires_clarification=False,
            clarification_field=missing,
        )

    pair = frozenset({left.measure_type, right.measure_type})
    base = ComparisonResult(
        status=ComparisonStatus.NOT_COMPARABLE_MEASURE,
        left_field=left.field_key,
        right_field=right.field_key,
        left_label=left.label,
        right_label=right.label,
        left_value=str(left.value),
        right_value=str(right.value),
        tolerance_percent=str(policy.tolerance_percent),
        period_label=left.period.label if left.period else None,
        evidence_ids=[left.id, right.id],
    )

    if left.period is None or right.period is None:
        base.status = ComparisonStatus.NOT_COMPARABLE_PERIOD
        base.explanation = (
            "At least one value has no explicit period, so the values cannot be compared."
        )
        return base

    if not periods_comparable(left.period, right.period):
        base.status = ComparisonStatus.NOT_COMPARABLE_PERIOD
        base.explanation = (
            f"Periods differ ({left.period.label} vs {right.period.label}) or granularity differs "
            f"({left.period.granularity} vs {right.period.granularity}). Values are not summed or "
            "annualized without an explicit rule."
        )
        return base

    if pair in NON_COMPARABLE_MEASURE_PAIRS:
        base.explanation = MEASURE_CAVEATS.get(
            pair,
            "These measures are not directly comparable without additional accounting context.",
        )
        if explanation_present:
            base.status = ComparisonStatus.CONTEXT_PROVIDED
            base.explanation += " The applicant's recorded explanation is attached for review."
        else:
            base.status = ComparisonStatus.NOT_COMPARABLE_MEASURE
            base.requires_clarification = policy.ask_for_context_on_measure_mismatch
            base.clarification_field = f"{left.measure_type}_vs_{right.measure_type}_context"
            base.clarification_reason = (
                "The two measures capture different things. A neutral explanation helps a human "
                "reviewer understand the difference; it is not evidence of a problem."
            )
        return base

    if pair not in COMPARABLE_MEASURE_PAIRS and left.measure_type != right.measure_type:
        base.explanation = "No configured comparison rule exists for these measures."
        return base

    difference = left.value - right.value
    percent = percentage_difference(right.value, left.value)
    base.difference = str(difference)
    base.percent_difference = str(percent) if percent is not None else None
    base.explanation = MEASURE_CAVEATS.get(pair, "")
    if is_within_tolerance(right.value, left.value, policy.tolerance_percent):
        base.status = ComparisonStatus.WITHIN_TOLERANCE
        base.explanation = (
            f"Difference is within the configured tolerance of {policy.tolerance_percent}%."
        )
    else:
        base.status = ComparisonStatus.DIFFERENCE_REQUIRES_CONTEXT
        base.requires_clarification = True
        base.clarification_field = f"{left.measure_type}_vs_{right.measure_type}_difference"
        base.clarification_reason = (
            "The values differ beyond the configured tolerance. This is a question to "
            "understand context, not a finding of fraud or misstatement."
        )
        if base.explanation:
            base.explanation += " "
        base.explanation += (
            "A difference is not automatically a discrepancy; timing, exemptions, and cash sales "
            "may explain it."
        )
    return base


def reconcile(
    facts: list[FactSnapshot],
    policy: ReconciliationPolicy,
    *,
    explanation_fields: set[str] | None = None,
) -> dict[str, object]:
    explanations = explanation_fields or set()
    primary = select_primary_facts(facts)
    duplicates = detect_duplicate_overlaps(facts)

    declared = primary.get("annual_sales") or primary.get("declared_sales")
    gst = primary.get("gst_turnover")
    bank = primary.get("bank_credits") or primary.get("bank_credit")
    cash = primary.get("cash_sales")

    comparisons: list[ComparisonResult] = []
    comparisons.append(
        compare_facts(
            declared,
            gst,
            policy,
            explanation_present="declared_sales_vs_gst_turnover_context" in explanations,
        )
    )
    comparisons.append(
        compare_facts(
            declared,
            bank,
            policy,
            explanation_present="declared_sales_vs_bank_credit_context" in explanations,
        )
    )
    comparisons.append(
        compare_facts(
            gst,
            bank,
            policy,
            explanation_present="gst_turnover_vs_bank_credit_context" in explanations,
        )
    )

    if cash is not None:
        comparisons.append(
            ComparisonResult(
                status=ComparisonStatus.CONTEXT_PROVIDED,
                left_field="cash_sales",
                right_field="declared_sales",
                left_label="Cash sales evidence",
                right_label="Applicant-declared annual sales",
                left_value=str(cash.value),
                right_value=str(declared.value) if declared else None,
                period_label=cash.period.label if cash.period else None,
                explanation=(
                    "A cash sales record is attached. Cash sales can explain why bank credits are "
                    "lower than declared sales, but the record is not treated as independently "
                    "verified unless a reviewer marks it so."
                ),
                requires_clarification=False,
                evidence_ids=[cash.id] + ([declared.id] if declared else []),
            )
        )

    missing_required = [
        field_key
        for field_key in policy.required_fields
        if not (
            (field_key == "declared_sales" and declared is not None)
            or (field_key == "bank_credit" and bank is not None)
            or field_key in primary
        )
    ]
    if missing_required:
        comparisons.append(
            ComparisonResult(
                status=ComparisonStatus.MISSING_INFORMATION,
                left_field="application",
                right_field="required_fields",
                left_label="Application evidence",
                right_label="Required comparison fields",
                explanation="Missing required information: " + ", ".join(missing_required),
                requires_clarification=False,
            )
        )

    comparisons.extend(duplicates)

    status_counts: dict[str, int] = {}
    for comparison in comparisons:
        status_counts[comparison.status.value] = status_counts.get(comparison.status.value, 0) + 1

    return {
        "tolerance_percent": str(policy.tolerance_percent),
        "policy_note": (
            "Configured comparison policy. Differences are questions for human review, not "
            "findings of fraud, misstatement, or ineligibility."
        ),
        "comparisons": [comparison.to_dict() for comparison in comparisons],
        "status_counts": status_counts,
        "missing_required_fields": missing_required,
        "has_blocking_difference": any(
            comparison.requires_clarification for comparison in comparisons
        ),
        "fact_count": len(facts),
        "selected_fact_ids": {key: fact.id for key, fact in primary.items()},
    }
