from __future__ import annotations

from typing import Any

from app.domain.workflow.plugins.base import (
    RuleClarificationItem,
    RuleEvaluationResult,
    RulePlugin,
)


class FinancialReconciliationPlugin(RulePlugin):
    """Domain rule plugin for MSME loan financial reconciliation.

    Compares declared sales vs GST turnover vs bank credits under explicit,
    deterministic policies with non-revenue bank caveats. Never makes an
    autonomous credit decision.
    """

    name = "financial_reconciliation"

    def __init__(self, tolerance_percent: int | float = 5) -> None:
        self.tolerance_percent = tolerance_percent

    def evaluate(
        self,
        application: Any,
        workflow: Any,
        facts: list[Any],
        documents: list[Any],
    ) -> RuleEvaluationResult:
        # Build comparison context from facts
        fact_dict = {
            f.field_key: f for f in facts if getattr(f, "provenance_status", None) != "superseded"
        }

        clarifications: list[RuleClarificationItem] = []
        comparisons: list[dict[str, Any]] = []

        sales_fact = fact_dict.get("annual_sales")
        gst_fact = fact_dict.get("gst_turnover")
        bank_fact = fact_dict.get("bank_credits")

        if sales_fact and gst_fact:
            try:
                from decimal import Decimal

                from app.domain.money import percentage_difference, to_decimal

                v1 = to_decimal(sales_fact.normalized_value)
                v2 = to_decimal(gst_fact.normalized_value)
                diff = percentage_difference(v1, v2)
                within = diff <= Decimal(str(self.tolerance_percent))

                comparison = {
                    "pair": ["annual_sales", "gst_turnover"],
                    "value_1": str(v1),
                    "value_2": str(v2),
                    "percentage_difference": float(diff),
                    "within_tolerance": within,
                    "requires_clarification": not within,
                    "clarification_field": "declared_sales_vs_gst_turnover_difference",
                    "clarification_reason": (
                        f"Declared sales ({v1:,.2f}) and GST turnover ({v2:,.2f}) "
                        f"differ by {diff:.1f}%, which exceeds the "
                        f"{self.tolerance_percent}% tolerance threshold."
                    ),
                }
                comparisons.append(comparison)

                if not within:
                    clarifications.append(
                        RuleClarificationItem(
                            field_key="declared_sales_vs_gst_turnover_difference",
                            question_text=(
                                "Your declared annual sales and GST turnover differ by "
                                "more than 5%. Could you explain any timing differences, "
                                "exempt supplies, or credit sales?"
                            ),
                            reason=comparison["clarification_reason"],
                            priority=100,
                        )
                    )
            except Exception:
                pass

        if bank_fact:
            comparisons.append(
                {
                    "measure": "bank_credits",
                    "normalized_value": bank_fact.normalized_value,
                    "caveat": (
                        "Bank credits are not revenue and may include loans, transfers, or "
                        "deposits."
                    ),
                    "requires_clarification": False,
                }
            )

        return RuleEvaluationResult(
            requires_clarification=len(clarifications) > 0,
            clarifications=clarifications,
            comparisons=comparisons,
            summary=f"Evaluated {len(comparisons)} financial reconciliation check(s).",
            flags=["reconciliation_active"],
            metadata={"tolerance_percent": self.tolerance_percent},
        )
