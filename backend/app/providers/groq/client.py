from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import ProviderAuthError, ProviderSchemaError
from app.providers.groq.errors import normalize_groq_error, normalize_groq_transport_error
from app.providers.groq.structured_output import build_response_format, parse_structured_output
from app.providers.interfaces import ReasoningResult

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.groq_base_url.rstrip("/")

    def api_key(self) -> str:
        if not self.settings.groq_api_key:
            raise ProviderAuthError("GROQ_API_KEY is not configured")
        value = self.settings.groq_api_key.get_secret_value().strip()
        if not value:
            raise ProviderAuthError("GROQ_API_KEY is not configured")
        return value

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        schema_model: type[BaseModel],
        schema_name: str,
        prompt_version: str,
    ) -> ReasoningResult:
        strict = self.settings.groq_strict_schema
        attempts = self.settings.groq_max_retries + 1
        started = time.perf_counter()
        schema_mode = "strict" if strict else "best_effort"
        request_id = uuid.uuid4().hex
        body = {
            "model": self.settings.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"untrusted_source_data": user_payload}, ensure_ascii=False
                    ),
                },
            ],
            "response_format": build_response_format(schema_model, name=schema_name, strict=strict),
            "max_completion_tokens": self.settings.groq_max_output_tokens,
            "reasoning_effort": self.settings.groq_reasoning_effort,
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key()}",
            "Content-Type": "application/json",
            "X-Client-Request-ID": request_id,
        }

        for attempt in range(attempts):
            try:
                with httpx.Client(
                    base_url=self.base_url,
                    timeout=self.settings.groq_timeout_seconds,
                ) as client:
                    response = client.post("/chat/completions", headers=headers, json=body)
                if response.status_code in RETRYABLE_STATUS and attempt < attempts - 1:
                    time.sleep(min(0.5 * (2**attempt), 4.0))
                    continue
                if response.status_code >= 400:
                    raise normalize_groq_error(response)
                return self._parse_response(
                    response,
                    schema_model=schema_model,
                    prompt_version=prompt_version,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    schema_mode=schema_mode,
                    request_id=response.headers.get("x-request-id", request_id),
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < attempts - 1:
                    time.sleep(min(0.5 * (2**attempt), 4.0))
                    continue
                raise normalize_groq_transport_error(exc) from exc
        raise normalize_groq_transport_error(httpx.TransportError("Groq retries exhausted"))

    def _parse_response(
        self,
        response: httpx.Response,
        *,
        schema_model: type[BaseModel],
        prompt_version: str,
        latency_ms: float,
        schema_mode: str,
        request_id: str,
    ) -> ReasoningResult:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderSchemaError("Groq returned a non-JSON response") from exc
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderSchemaError("Groq response did not include a completion")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ProviderSchemaError("Groq response did not include message content")
        validated = parse_structured_output(schema_model, content)
        usage = payload.get("usage") or {}
        return ReasoningResult(
            data=validated.model_dump(),
            model=payload.get("model") or self.settings.groq_model,
            provider="groq",
            prompt_version=prompt_version,
            latency_ms=round(latency_ms, 2),
            request_id=request_id,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            schema_mode=schema_mode,
            raw_metadata={"finish_reason": choices[0].get("finish_reason")},
        )
