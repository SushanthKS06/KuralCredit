from __future__ import annotations

from typing import Any

from app.domain.workflow.plugins.base import (
    RuleClarificationItem,
    RuleEvaluationResult,
    RulePlugin,
)


class SupportTriagePlugin(RulePlugin):
    """Domain rule plugin for Customer Support Issue Triage.

    Evaluates issue description completeness, urgency severity, and contact
    channel preferences. Generates neutral clarification questions for human triage.
    """

    name = "support_triage"

    def evaluate(
        self,
        application: Any,
        workflow: Any,
        facts: list[Any],
        documents: list[Any],
    ) -> RuleEvaluationResult:
        fact_dict = {
            f.field_key: f for f in facts if getattr(f, "provenance_status", None) != "superseded"
        }

        clarifications: list[RuleClarificationItem] = []
        comparisons: list[dict[str, Any]] = []

        issue_fact = fact_dict.get("customer_issue")
        urgency_fact = fact_dict.get("urgency")

        # Check: if urgency is high/critical, ensure sufficient symptom details
        if urgency_fact and issue_fact:
            urgency_val = str(urgency_fact.normalized_value or urgency_fact.raw_value).lower()
            issue_val = str(issue_fact.normalized_value or issue_fact.raw_value).strip()

            if urgency_val in {"high", "critical"} and len(issue_val) < 20:
                reason = (
                    "High or critical urgency reports require specific error messages "
                    "or impact details for immediate technician routing."
                )
                clarifications.append(
                    RuleClarificationItem(
                        field_key="high_urgency_symptom_detail",
                        question_text=(
                            "Because this issue is marked high urgency, could you provide "
                            "the exact error message or how many users are currently affected?"
                        ),
                        reason=reason,
                        priority=100,
                    )
                )
                comparisons.append(
                    {
                        "rule": "high_urgency_detail_check",
                        "urgency": urgency_val,
                        "issue_length": len(issue_val),
                        "requires_clarification": True,
                        "reason": reason,
                    }
                )

        return RuleEvaluationResult(
            requires_clarification=len(clarifications) > 0,
            clarifications=clarifications,
            comparisons=comparisons,
            summary=f"Support triage rule checked {len(comparisons)} condition(s).",
            flags=["triage_evaluated"],
            metadata={},
        )
