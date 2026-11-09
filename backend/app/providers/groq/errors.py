from __future__ import annotations

from typing import Any

import httpx

from app.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def normalize_groq_error(response: httpx.Response) -> Exception:
    status = response.status_code
    message = _extract_message(response)
    if status in {401, 403}:
        return ProviderAuthError(
            "Groq rejected the API key or model access. Verify GROQ_API_KEY and model permissions."
        )
    if status == 429:
        return ProviderRateLimitError(
            "Groq rate limit reached. Retry with backoff.", retryable=True
        )
    if status >= 500:
        return ProviderUnavailableError(
            f"Groq is temporarily unavailable (HTTP {status}). {message}".strip(), retryable=True
        )
    return ProviderResponseError(
        f"Groq rejected the request (HTTP {status}). {message}".strip(), retryable=False
    )


def normalize_groq_transport_error(exc: Exception) -> Exception:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderTimeoutError("Groq request timed out.", retryable=True)
    return ProviderUnavailableError("Could not reach Groq.", retryable=True)


def _extract_message(response: httpx.Response) -> str:
    try:
        body: Any = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])[:300]
        if body.get("message"):
            return str(body["message"])[:300]
    return ""
