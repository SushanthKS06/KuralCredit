from __future__ import annotations

from app.providers.groq.structured_output import (
    ApplicantFactExtraction,
)


def test_groq_pydantic_schemas():
    data = {
        "candidate_facts": [
            {
                "field_key": "annual_sales",
                "raw_value": "18 lakh",
                "normalized_candidate": "1800000",
                "currency": "INR",
                "period_start": "2025-04-01",
                "period_end": "2026-03-31",
                "source_turn_id": "turn-1",
                "evidence_quote": "Sales were 18 lakh",
                "confidence_estimate": 0.95,
                "ambiguity_reason": None,
            }
        ],
        "missing_fields": [],
        "clarification_candidates": [],
        "unsupported_claims": [],
    }
    parsed = ApplicantFactExtraction.model_validate(data)
    assert len(parsed.candidate_facts) == 1
    assert parsed.candidate_facts[0].field_key == "annual_sales"
