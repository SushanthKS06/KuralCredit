from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FactDefinition:
    field_key: str
    label: str
    measure_type: str
    value_type: Literal["amount", "text", "number"]
    source_type: str
    default_period: Literal["previous_fy"] | None = None


FACT_DEFINITIONS: dict[str, FactDefinition] = {
    "business_type": FactDefinition(
        field_key="business_type",
        label="Business type",
        measure_type="business_context",
        value_type="text",
        source_type="applicant_text",
    ),
    "years_in_operation": FactDefinition(
        field_key="years_in_operation",
        label="Years in operation",
        measure_type="business_context",
        value_type="number",
        source_type="applicant_text",
    ),
    "annual_sales": FactDefinition(
        field_key="annual_sales",
        label="Applicant-declared annual sales",
        measure_type="declared_sales",
        value_type="amount",
        source_type="applicant_text",
        default_period="previous_fy",
    ),
    "gst_turnover": FactDefinition(
        field_key="gst_turnover",
        label="GST-reported turnover",
        measure_type="gst_turnover",
        value_type="amount",
        source_type="GST_document",
        default_period="previous_fy",
    ),
    "cash_sales": FactDefinition(
        field_key="cash_sales",
        label="Cash sales",
        measure_type="cash_sales",
        value_type="amount",
        source_type="applicant_text",
        default_period="previous_fy",
    ),
    "sales_register_total": FactDefinition(
        field_key="sales_register_total",
        label="Sales register total",
        measure_type="sales_register_total",
        value_type="amount",
        source_type="sales_register",
        default_period="previous_fy",
    ),
    "bank_credits": FactDefinition(
        field_key="bank_credits",
        label="Bank statement credits",
        measure_type="bank_credit",
        value_type="amount",
        source_type="bank_statement",
    ),
}

FIELD_ALIASES = {
    "bank_credit": "bank_credits",
    "declared_sales": "annual_sales",
}

FINANCIAL_MEASURES = frozenset(
    {
        "declared_sales",
        "gst_turnover",
        "bank_credit",
        "cash_sales",
        "sales_register_total",
    }
)


def resolve_field(field_key: str, workflow_id: str | None = None) -> FactDefinition | None:
    normalized = FIELD_ALIASES.get(field_key, field_key)
    if normalized in FACT_DEFINITIONS:
        return FACT_DEFINITIONS[normalized]
    try:
        from app.domain.workflow.registry import get_workflow_registry

        registry = get_workflow_registry()
        if workflow_id:
            try:
                wf = registry.get(workflow_id)
                if normalized in wf.field_by_id:
                    f = wf.field_by_id[normalized]
                    vtype: Literal["amount", "text", "number"] = (
                        "amount"
                        if f.type == "money"
                        else "number"
                        if f.type == "number"
                        else "text"
                    )
                    return FactDefinition(
                        field_key=f.id,
                        label=f.label,
                        measure_type=f.measure_type,
                        value_type=vtype,
                        source_type=f.source_type,
                        default_period=f.default_period
                        if f.default_period in ("previous_fy", None)
                        else None,
                    )
            except Exception:
                pass
        for summary in registry.list_workflows():
            try:
                wf = registry.get(summary.workflow_id)
                if normalized in wf.field_by_id:
                    f = wf.field_by_id[normalized]
                    vtype = (
                        "amount"
                        if f.type == "money"
                        else "number"
                        if f.type == "number"
                        else "text"
                    )
                    return FactDefinition(
                        field_key=f.id,
                        label=f.label,
                        measure_type=f.measure_type,
                        value_type=vtype,
                        source_type=f.source_type,
                        default_period=f.default_period
                        if f.default_period in ("previous_fy", None)
                        else None,
                    )
            except Exception:
                continue
    except Exception:
        pass
    return None


def target_field_payload(
    field_keys: list[str], workflow_id: str | None = None
) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for field_key in field_keys:
        definition = resolve_field(field_key, workflow_id)
        if definition is None:
            continue
        payload.append(
            {
                "field_key": definition.field_key,
                "label": definition.label,
                "measure_type": definition.measure_type,
                "value_type": definition.value_type,
            }
        )
    return payload
