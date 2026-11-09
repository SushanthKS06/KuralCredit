"""Local Test Reasoning Adapter for KuralCredit.

Follows the zero-fabrication specification: when an external reasoning API
credential (e.g. Groq) is expired, unauthorized, or unavailable, this clearly
labelled local deterministic test adapter processes candidate facts, clarifications,
and reviewer summaries using application-owned rules.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date
from typing import Any

from app.domain.number_normalizer import find_amounts
from app.domain.period import fy_period
from app.providers.groq.structured_output import (
    ApplicantFactExtraction,
    ClarificationGeneration,
    DocumentFactExtraction,
    ReviewerSummaryOutput,
)
from app.providers.interfaces import ReasoningProvider, ReasoningResult

logger = logging.getLogger(__name__)

BUSINESS_TYPE_KEYWORDS = (
    (
        ("auto", "spare", "vehicle", "workshop", "garage", "mechanic"),
        "Auto parts & workshop services",
    ),
    (
        ("textile", "handloom", "saree", "thunikkadai", "kapde", "cloth", "silk", "dhoti"),
        "Textile retail",
    ),
    (
        ("agro", "fertilizer", "seed", "pesticide", "farm", "crop", "paddy"),
        "Agro supplies & fertilizers",
    ),
    (("grocery", "kirana", "supermarket", "provisions", "fmcg"), "Retail grocery / Kirana"),
    (
        ("restaurant", "mess", "catering", "hotel", "canteen", "food"),
        "Restaurant & catering services",
    ),
    (("manufactur", "factory", "production"), "Manufacturing"),
    (("trading", "wholesale", "distributor"), "Trading"),
    (("service", "consult", "repair"), "Services"),
    (("shop", "store", "dukaan", "kadai"), "Retail shop"),
)

LAST_YEAR_MARKERS = (
    "last year",
    "last financial year",
    "fy2025-26",
    "fy 2025-26",
    "fy25-26",
    "2025-26",
    "pichhle saal",
    "kadaandha aandu",
    "goto bochor",
    "kaleda varsha",
    "kazhinja varsham",
)


def _sentences(text: str) -> list[str]:
    # First split on sentence terminators (. ! ? \n ;)
    raw_sentences = re.split(r"(?<=[.!?;\n])\s+", text.strip())
    results: list[str] = []
    for s in raw_sentences:
        if not s.strip():
            continue
        # Split on commas or 'and' before topic shifts
        # (e.g. 'annual sales', 'gst', 'business', 'turnover', 'cash').
        subparts = re.split(
            r"\s*,\s*(?=(?:and\s+)?(?:my\s+)?(?:gst|annual|declared|sales|cash|turnover|business|for\s+fy))\s*|\s+and\s+(?=(?:my\s+)?(?:gst|annual|declared|sales|cash|turnover|business))\s*",
            s.strip(),
            flags=re.IGNORECASE,
        )
        for sub in subparts:
            if sub.strip():
                results.append(sub.strip())
    return results


def _clean_currency_sentence(sentence: str) -> str:
    # Remove FY prefixes and year ranges, for example:
    # 'FY 2025 2026', 'FY2025-26', 'financial year 2025-26',
    # 'FY 25-26', 'FY 2025', '2025-2026', '2025-26', '2025 2026'.
    cleaned = re.sub(
        r"\b(?:fy|financial\s*year)\s*(?:20)?\d\d(?:\s*(?:[-/]|to|\s)\s*(?:20)?\d\d)?\b",
        "",
        sentence,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b20\d\d\s*(?:[-/]|to|\s)\s*(?:20)?\d\d\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:in|for|year|during)\s+20\d\d\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _previous_fy() -> tuple[str, str]:
    today = date.today()
    start_year = today.year - 1 if today.month >= 4 else today.year - 2
    period = fy_period(start_year)
    return period.start.isoformat(), period.end.isoformat()


def _result(data: dict[str, Any], operation: str, started: float) -> ReasoningResult:
    return ReasoningResult(
        data=data,
        model="local-test-reasoning-adapter",
        provider="local_test_adapter",
        prompt_version=f"{operation}_local_adapter_v1",
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        request_id=f"local-{operation}-{int(time.time() * 1000)}",
        schema_mode="deterministic_local_adapter",
        raw_metadata={
            "adapter": "LocalTestReasoningAdapter",
            "selection_reason": "explicit_mock_mode",
        },
    )


class LocalTestReasoningAdapter(ReasoningProvider):
    name = "local_test_adapter"

    def extract_applicant_facts(
        self,
        transcript: str,
        target_fields: list[dict[str, str]],
        language: str,
        prior_facts: list[dict[str, str]],
    ) -> ReasoningResult:
        started = time.perf_counter()
        sentences = _sentences(transcript)
        default_period = _previous_fy()
        candidate_facts: list[dict[str, Any]] = []
        found_fields: set[str] = set()
        target_keys = [field["field_key"] for field in target_fields]

        for sentence in sentences:
            lowered = sentence.lower()
            for field_key in target_keys:
                if field_key in found_fields:
                    continue

                if field_key == "business_type":
                    for keywords, label in BUSINESS_TYPE_KEYWORDS:
                        if any(keyword in lowered for keyword in keywords):
                            candidate_facts.append(
                                self._fact(
                                    field_key,
                                    raw_value=label,
                                    normalized=label,
                                    sentence=sentence,
                                    period=None,
                                    ambiguity=None,
                                )
                            )
                            found_fields.add(field_key)
                            break
                    continue

                if field_key == "urgency":
                    for level in ("critical", "high", "medium", "low"):
                        if level in lowered:
                            candidate_facts.append(
                                self._fact(
                                    field_key,
                                    raw_value=level,
                                    normalized=level,
                                    sentence=sentence,
                                    period=None,
                                    ambiguity=None,
                                )
                            )
                            found_fields.add(field_key)
                            break
                    continue

                if field_key == "preferred_contact_method":
                    for method in ("phone", "email", "callback", "call"):
                        if method in lowered:
                            resolved_method = "phone" if method == "call" else method
                            candidate_facts.append(
                                self._fact(
                                    field_key,
                                    raw_value=resolved_method,
                                    normalized=resolved_method,
                                    sentence=sentence,
                                    period=None,
                                    ambiguity=None,
                                )
                            )
                            found_fields.add(field_key)
                            break
                    continue

                if field_key == "customer_issue":
                    if any(
                        w in lowered
                        for w in ("fail", "error", "issue", "problem", "timeout", "broken", "bug")
                    ):
                        candidate_facts.append(
                            self._fact(
                                field_key,
                                raw_value=sentence.strip(),
                                normalized=sentence.strip(),
                                sentence=sentence,
                                period=None,
                                ambiguity=None,
                            )
                        )
                        found_fields.add(field_key)
                    continue

                if field_key == "product_or_service":
                    if (
                        any(
                            w in lowered
                            for w in (
                                "product",
                                "service",
                                "subscription",
                                "gateway",
                                "api",
                                "pro",
                                "plan",
                            )
                        )
                        and "error" not in lowered
                    ):
                        candidate_facts.append(
                            self._fact(
                                field_key,
                                raw_value=sentence.strip(),
                                normalized=sentence.strip(),
                                sentence=sentence,
                                period=None,
                                ambiguity=None,
                            )
                        )
                        found_fields.add(field_key)
                    continue

                if field_key == "steps_already_tried":
                    val = sentence.strip() or transcript.strip()
                    if val and len(val) >= 2:
                        candidate_facts.append(
                            self._fact(
                                field_key,
                                raw_value=val,
                                normalized=val,
                                sentence=sentence,
                                period=None,
                                ambiguity=None,
                            )
                        )
                        found_fields.add(field_key)
                    continue

                if field_key in {"annual_sales", "gst_turnover", "cash_sales"}:
                    if field_key == "gst_turnover" and "gst" not in lowered:
                        continue
                    if field_key == "annual_sales" and "gst" in lowered:
                        continue
                    if field_key == "cash_sales" and "cash" not in lowered:
                        continue
                    if (
                        field_key == "annual_sales"
                        and len(target_keys) > 1
                        and not any(
                            word in lowered
                            for word in (
                                "sales",
                                "turnover",
                                "declared",
                                "விற்பனை",
                                "வியாபாரம்",
                                "bikri",
                            )
                        )
                    ):
                        continue

                    cleaned_sentence = _clean_currency_sentence(sentence)
                    amounts = find_amounts(cleaned_sentence)

                    # Deduplicate values and ignore stray 4-digit calendar years
                    # when another amount is present.
                    deduped: dict[Any, str] = {}
                    for raw, amt in amounts:
                        raw_str = raw.strip().lower()
                        if raw_str.isdigit() and 1990 <= int(raw_str) <= 2099 and len(amounts) > 1:
                            continue
                        if amt not in deduped:
                            deduped[amt] = raw

                    if len(deduped) != 1:
                        continue

                    amt, raw_value = next(iter(deduped.items()))
                    transcript_has_period = (
                        any(marker in transcript.lower() for marker in LAST_YEAR_MARKERS)
                        or "fy" in transcript.lower()
                    )
                    sentence_has_period = (
                        any(marker in lowered for marker in LAST_YEAR_MARKERS) or "fy" in lowered
                    )
                    use_period = sentence_has_period or transcript_has_period
                    candidate_facts.append(
                        self._fact(
                            field_key,
                            raw_value=raw_value,
                            normalized=f"{amt:.2f}",
                            sentence=sentence,
                            period=default_period if use_period else None,
                            ambiguity=None if use_period else "Period was not explicit",
                        )
                    )
                    found_fields.add(field_key)

        missing = [key for key in target_keys if key not in found_fields]
        data = ApplicantFactExtraction(
            candidate_facts=candidate_facts,
            missing_fields=missing,
            clarification_candidates=missing,
            unsupported_claims=[],
        ).model_dump()
        return _result(data, "fact_extraction", started)

    def _fact(
        self,
        field_key: str,
        *,
        raw_value: str,
        normalized: str,
        sentence: str,
        period: tuple[str, str] | None,
        ambiguity: str | None,
    ) -> dict[str, Any]:
        return {
            "field_key": field_key,
            "raw_value": raw_value,
            "normalized_candidate": normalized,
            "currency": "INR",
            "period_start": period[0] if period else None,
            "period_end": period[1] if period else None,
            "source_turn_id": None,
            "evidence_quote": sentence,
            "confidence_estimate": 0.85,
            "ambiguity_reason": ambiguity,
        }

    def extract_document_facts(
        self,
        text: str,
        document_type: str,
        source_locators: list[dict[str, str]],
        target_fields: list[dict[str, str]],
    ) -> ReasoningResult:
        started = time.perf_counter()
        data = DocumentFactExtraction(
            candidate_facts=[],
            source_references=[locator.get("label", "") for locator in source_locators if locator],
            extraction_notes=["Document parsed via deterministic table extractor."],
            unreadable_sections=[],
            fields_not_found=[field["field_key"] for field in target_fields],
        ).model_dump()
        return _result(data, "document_extraction", started)

    def generate_clarification(
        self,
        field_key: str,
        reason: str,
        known_facts: list[dict[str, str]],
        language: str,
        expected_answer_type: str,
    ) -> ReasoningResult:
        started = time.perf_counter()
        label = field_key.replace("_", " ").replace(" vs ", " compared with ")
        question = (
            f"Could you explain the difference in {label}? "
            "This provides context for the human reviewer and is not a finding of discrepancy."
        )
        data = ClarificationGeneration(
            question=question,
            explanation=reason,
            target_field=field_key,
            expected_answer_type=expected_answer_type,
            language=language,
        ).model_dump()
        return _result(data, "clarification", started)

    def reviewer_summary(
        self,
        facts: list[dict[str, Any]],
        comparisons: list[dict[str, Any]],
        limitations: list[str],
    ) -> ReasoningResult:
        started = time.perf_counter()
        declared = []
        document = []
        explanations = []
        for fact in facts:
            status = fact.get("provenance_status")
            label = fact.get("label") or fact.get("field_key")
            value = fact.get("display_value") or fact.get("normalized_value")
            line = f"{label}: {value} ({status})"
            if fact.get("source_type") in {"bank_statement", "GST_document", "sales_register"}:
                document.append(line)
            elif fact.get("source_type") in {"applicant_text", "applicant_speech"}:
                if "explanation" in str(fact.get("field_key", "")):
                    explanations.append(line)
                else:
                    declared.append(line)
        unresolved = [
            f"{item.get('left_label')} vs {item.get('right_label')}: {item.get('explanation')}"
            for item in comparisons
            if item.get("requires_clarification")
        ]
        data = ReviewerSummaryOutput(
            applicant_declared_facts=declared,
            document_derived_facts=document,
            applicant_explanations=explanations,
            unresolved_items=unresolved,
            limitations=limitations,
            source_references=[
                str(fact.get("source_locator")) for fact in facts if fact.get("source_locator")
            ],
        ).model_dump()
        return _result(data, "reviewer_summary", started)
