from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.exceptions import ProviderSchemaError


class CandidateFact(BaseModel):
    field_key: str
    raw_value: str
    normalized_candidate: str | None = None
    currency: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    source_turn_id: str | None = None
    evidence_quote: str
    confidence_estimate: float | None = None
    ambiguity_reason: str | None = None


class ApplicantFactExtraction(BaseModel):
    candidate_facts: list[CandidateFact]
    missing_fields: list[str]
    clarification_candidates: list[str]
    unsupported_claims: list[str]


class DocumentCandidateFact(BaseModel):
    field_key: str
    raw_value: str
    normalized_candidate: str | None = None
    currency: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    measure_type: str
    source_locator: str
    evidence_quote: str
    confidence_estimate: float | None = None
    notes: str | None = None


class DocumentFactExtraction(BaseModel):
    candidate_facts: list[DocumentCandidateFact]
    source_references: list[str]
    extraction_notes: list[str]
    unreadable_sections: list[str]
    fields_not_found: list[str]


class ClarificationGeneration(BaseModel):
    question: str
    explanation: str
    target_field: str
    expected_answer_type: str
    language: str


class ReviewerSummaryOutput(BaseModel):
    applicant_declared_facts: list[str]
    document_derived_facts: list[str]
    applicant_explanations: list[str]
    unresolved_items: list[str]
    limitations: list[str]
    source_references: list[str]


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "applicant_fact_extraction": ApplicantFactExtraction,
    "document_fact_extraction": DocumentFactExtraction,
    "clarification_generation": ClarificationGeneration,
    "reviewer_summary": ReviewerSummaryOutput,
}


def _enforce_strict(node: Any) -> Any:
    if isinstance(node, dict):
        updated = {key: _enforce_strict(value) for key, value in node.items()}
        if updated.get("type") == "object" or "properties" in updated:
            updated.setdefault("additionalProperties", False)
            if "properties" in updated:
                updated["required"] = list(updated["properties"].keys())
        return updated
    if isinstance(node, list):
        return [_enforce_strict(item) for item in node]
    return node


def build_json_schema(model: type[BaseModel], *, strict: bool) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    if strict:
        schema = _enforce_strict(schema)
    return schema


def build_response_format(model: type[BaseModel], *, name: str, strict: bool) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": strict,
            "schema": build_json_schema(model, strict=strict),
        },
    }


def parse_structured_output(model: type[BaseModel], content: str) -> BaseModel:
    if not content or not content.strip():
        raise ProviderSchemaError("Groq returned an empty structured response")
    stripped = content.strip()
    if stripped.startswith("```"):
        raise ProviderSchemaError("Groq returned fenced text instead of schema-valid JSON")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ProviderSchemaError("Groq response was not valid JSON") from exc
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ProviderSchemaError(
            "Groq response did not match the required schema",
            details={"errors": exc.errors()[:5]},
        ) from exc
