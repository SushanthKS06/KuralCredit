from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.observability.redaction import redact_text
from app.prompts.registry import PromptRegistry
from app.providers.groq.client import GroqClient
from app.providers.groq.structured_output import (
    ApplicantFactExtraction,
    ClarificationGeneration,
    DocumentFactExtraction,
    ReviewerSummaryOutput,
)
from app.providers.interfaces import ReasoningProvider, ReasoningResult

logger = logging.getLogger(__name__)


class GroqReasoningProvider(ReasoningProvider):
    """Groq GPT-OSS reasoning provider.

    Real mode is strict: provider failures propagate to the caller as typed
    ProviderError instances. There is no local heuristic fallback, so a failed
    Groq request can never look like a successful model extraction.
    """

    name = "groq"

    def __init__(self, settings: Settings, registry: PromptRegistry | None = None) -> None:
        self.settings = settings
        self.client = GroqClient(settings)
        self.prompts = registry or PromptRegistry()

    def _system(self, prompt_name: str) -> tuple[str, str]:
        safety = self.prompts.get("safety_policy").text
        task = self.prompts.get(prompt_name)
        return f"{safety}\n\n{task.text}", task.version

    def _truncate(self, text: str) -> str:
        limit = self.settings.groq_max_input_chars
        if len(text) <= limit:
            return text
        return text[:limit] + "\n[TRUNCATED: input exceeded configured limit]"

    def extract_applicant_facts(
        self,
        transcript: str,
        target_fields: list[dict[str, str]],
        language: str,
        prior_facts: list[dict[str, str]],
    ) -> ReasoningResult:
        system, version = self._system("fact_extraction")
        return self.client.chat_json(
            system_prompt=system,
            user_payload={
                "transcript": self._truncate(redact_text(transcript)),
                "target_fields": target_fields,
                "language": language,
                "prior_facts": prior_facts,
            },
            schema_model=ApplicantFactExtraction,
            schema_name="applicant_fact_extraction",
            prompt_version=version,
        )

    def extract_document_facts(
        self,
        text: str,
        document_type: str,
        source_locators: list[dict[str, str]],
        target_fields: list[dict[str, str]],
    ) -> ReasoningResult:
        system, version = self._system("document_summary")
        return self.client.chat_json(
            system_prompt=system,
            user_payload={
                "document_text": self._truncate(redact_text(text)),
                "document_type": document_type,
                "source_locators": source_locators,
                "target_fields": target_fields,
            },
            schema_model=DocumentFactExtraction,
            schema_name="document_fact_extraction",
            prompt_version=version,
        )

    def generate_clarification(
        self,
        field_key: str,
        reason: str,
        known_facts: list[dict[str, str]],
        language: str,
        expected_answer_type: str,
    ) -> ReasoningResult:
        system, version = self._system("clarification")
        return self.client.chat_json(
            system_prompt=system,
            user_payload={
                "field_key": field_key,
                "reason": reason,
                "known_facts": known_facts,
                "language": language,
                "expected_answer_type": expected_answer_type,
            },
            schema_model=ClarificationGeneration,
            schema_name="clarification_generation",
            prompt_version=version,
        )

    def reviewer_summary(
        self,
        facts: list[dict[str, Any]],
        comparisons: list[dict[str, Any]],
        limitations: list[str],
    ) -> ReasoningResult:
        system, version = self._system("reviewer_summary")
        return self.client.chat_json(
            system_prompt=system,
            user_payload={
                "facts": facts,
                "comparisons": comparisons,
                "limitations": limitations,
            },
            schema_model=ReviewerSummaryOutput,
            schema_name="reviewer_summary",
            prompt_version=version,
        )
