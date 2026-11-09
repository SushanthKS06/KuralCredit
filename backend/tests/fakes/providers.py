from __future__ import annotations

import io
import math
import re
import struct
import time
import wave
from datetime import date
from typing import Any

from app.domain.number_normalizer import find_amounts
from app.domain.period import fy_period
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.groq.structured_output import (
    ApplicantFactExtraction,
    ClarificationGeneration,
    DocumentFactExtraction,
    ReviewerSummaryOutput,
)
from app.providers.interfaces import (
    ReasoningProvider,
    ReasoningResult,
    SpeechToTextProvider,
    SynthesisResult,
    TextToSpeechProvider,
    TranscriptionResult,
)
from app.providers.registry import ProviderRegistry

FAKE_TRANSCRIPTS = {
    "ta-IN": (
        "En kadai oru thunikkadai. Kadaandha aandu sales 18 lakh rubai. "
        "GST turnover 16 lakh 50 thousand."
    ),
    "hi-IN": (
        "Meri dukaan kapde bechti hai. Pichhle saal ki sales 18 lakh rupaye thi. "
        "GST turnover 16 lakh 50 thousand tha."
    ),
    "en-IN": (
        "My business is a textile shop. Last year sales were 18 lakh rupees. "
        "GST turnover was 16 lakh 50 thousand."
    ),
    "bn-IN": "Amar dokan bastra bikri kore. Goto bochorer sales chilo 18 lakh taka.",
    "gu-IN": "Mari dukan kapda veche. Gaya varsh ni sales 18 lakh hti.",
    "kn-IN": "Nanna angadi batte maratu. Kaleda varsha sales 18 lakh rupayi.",
    "ml-IN": "Ente kadasil vasthram vilkkunnu. Kazhinja varsham sales 18 lakh rupaya.",
    "mr-IN": "Mazi dukan kapde vikte. Magchya varshachi sales 18 lakh rupaye hoti.",
    "pa-IN": "Meri dukan kapde vechdi hai. Pichhle saal di sales 18 lakh si.",
    "te-IN": "Na dukanam battalu ammutundi. Gata saal sales 18 lakh rupayalu.",
}

BUSINESS_TYPE_KEYWORDS = (
    (("textile", "thunikkadai", "kapde", "cloth", "bastra", "batte", "vasthram"), "Textile retail"),
    (("manufactur", "factory", "production"), "Manufacturing"),
    (("trading", "wholesale", "distributor"), "Trading"),
    (("service", "consult", "salon", "repair"), "Services"),
    (("shop", "dukaan", "kadai", "angadi", "dokan", "dukan", "store"), "Retail shop"),
)

LAST_YEAR_MARKERS = (
    "last year",
    "last financial year",
    "pichhle saal",
    "kadaandha aandu",
    "goto bochor",
    "kaleda varsha",
    "kazhinja varsham",
    "magchya varsha",
    "gata saal",
    "gaya varsh",
)


def _tone_wav(duration_seconds: float = 0.45, sample_rate: int = 16000) -> bytes:
    frames = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            amplitude = int(1200 * math.sin(2 * math.pi * 440 * index / sample_rate))
            handle.writeframesraw(struct.pack("<h", amplitude))
    return buffer.getvalue()


class FakeSpeechProvider(SpeechToTextProvider, TextToSpeechProvider):
    name = "fake"

    def __init__(
        self,
        catalog: CapabilityCatalog | None = None,
        tts_model: str = "timbre-v2.5",
    ) -> None:
        self.catalog = catalog
        self.tts_model = tts_model

    def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        language: str,
    ) -> TranscriptionResult:
        started = time.perf_counter()
        transcript = FAKE_TRANSCRIPTS.get(language, FAKE_TRANSCRIPTS["en-IN"])
        return TranscriptionResult(
            transcript=transcript,
            language=language,
            detected_language=language,
            model="fake-prisma",
            provider=self.name,
            request_id="fake-stt",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            raw_metadata={"test_double": True},
        )

    def synthesize(self, text: str, language: str, voice: str) -> SynthesisResult:
        if self.catalog is not None:
            self.catalog.validate_voice(language, voice, self.tts_model)
        started = time.perf_counter()
        return SynthesisResult(
            audio=_tone_wav(),
            content_type="audio/wav",
            model="fake-timbre",
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            request_id="fake-tts",
            raw_metadata={"test_double": True},
        )


def _previous_fy(today: date | None = None) -> tuple[str, str]:
    today = today or date.today()
    start_year = today.year if today.month >= 4 else today.year - 1
    start_year -= 1
    period = fy_period(start_year)
    return period.start.isoformat(), period.end.isoformat()


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text) if part.strip()]


def _result(data: dict[str, Any], operation: str, started: float) -> ReasoningResult:
    return ReasoningResult(
        data=data,
        model="fake-gpt-oss",
        provider="fake",
        prompt_version=f"{operation}_fake_v1",
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        request_id=f"fake-{operation}",
        schema_mode="fake",
        raw_metadata={"test_double": True},
    )


class FakeReasoningProvider(ReasoningProvider):
    name = "fake"

    def extract_applicant_facts(
        self,
        transcript: str,
        target_fields: list[dict[str, str]],
        language: str,
        prior_facts: list[dict[str, str]],
    ) -> ReasoningResult:
        started = time.perf_counter()
        sentences = _sentences(transcript)
        period = _previous_fy()
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
                if field_key == "years_in_operation":
                    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|aandu|saal)", lowered)
                    if match:
                        candidate_facts.append(
                            self._fact(
                                field_key,
                                raw_value=match.group(0),
                                normalized=match.group(1),
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
                    if field_key == "annual_sales" and not any(
                        word in lowered for word in ("sales", "turnover", "விற்பனை")
                    ):
                        continue
                    amounts = find_amounts(sentence)
                    if len(amounts) != 1:
                        continue
                    raw_value, amount = amounts[0]
                    has_period_marker = any(marker in lowered for marker in LAST_YEAR_MARKERS)
                    candidate_facts.append(
                        self._fact(
                            field_key,
                            raw_value=raw_value,
                            normalized=f"{amount:.2f}",
                            sentence=sentence,
                            period=period if has_period_marker else None,
                            ambiguity=None if has_period_marker else "Period was not explicit",
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
            "confidence_estimate": 0.7,
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
            extraction_notes=[
                "Fake document extraction used by the test suite. "
                "CSV and XLSX uploads use deterministic parsers."
            ],
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
            f"Could you explain what is included in the {label}? "
            "This helps a reviewer understand the records and is not a finding of a problem."
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


def build_fake_registry(settings, catalog: CapabilityCatalog) -> ProviderRegistry:
    registry = ProviderRegistry(settings, catalog)
    registry._stt = FakeSpeechProvider(catalog)
    registry._tts = FakeSpeechProvider(catalog, settings.gnani_tts_model)
    registry._reasoning = FakeReasoningProvider()
    return registry
