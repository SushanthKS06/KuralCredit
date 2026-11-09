from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptionResult:
    transcript: str
    language: str
    detected_language: str | None
    model: str
    provider: str
    request_id: str | None = None
    latency_ms: float = 0.0
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    audio: bytes
    content_type: str
    model: str
    provider: str
    latency_ms: float = 0.0
    request_id: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult:
    data: dict[str, Any]
    model: str
    provider: str
    prompt_version: str
    latency_ms: float = 0.0
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    schema_mode: str = "strict"
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class SpeechToTextProvider(ABC):
    name: str

    @abstractmethod
    def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        language: str,
    ) -> TranscriptionResult:
        raise NotImplementedError


class TextToSpeechProvider(ABC):
    name: str

    @abstractmethod
    def synthesize(self, text: str, language: str, voice: str) -> SynthesisResult:
        raise NotImplementedError


class ReasoningProvider(ABC):
    name: str

    @abstractmethod
    def extract_applicant_facts(
        self,
        transcript: str,
        target_fields: list[dict[str, str]],
        language: str,
        prior_facts: list[dict[str, str]],
    ) -> ReasoningResult:
        raise NotImplementedError

    @abstractmethod
    def extract_document_facts(
        self,
        text: str,
        document_type: str,
        source_locators: list[dict[str, str]],
        target_fields: list[dict[str, str]],
    ) -> ReasoningResult:
        raise NotImplementedError

    @abstractmethod
    def generate_clarification(
        self,
        field_key: str,
        reason: str,
        known_facts: list[dict[str, str]],
        language: str,
        expected_answer_type: str,
    ) -> ReasoningResult:
        raise NotImplementedError

    @abstractmethod
    def reviewer_summary(
        self,
        facts: list[dict[str, Any]],
        comparisons: list[dict[str, Any]],
        limitations: list[str],
    ) -> ReasoningResult:
        raise NotImplementedError


class DocumentExtractionProvider(ABC):
    name: str

    @abstractmethod
    def extract(self, text: str, document_type: str) -> ReasoningResult:
        raise NotImplementedError
