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


def normalize_gnani_error(response: httpx.Response) -> Exception:
    status = response.status_code
    message = _extract_message(response)
    if status in {401, 403}:
        return ProviderAuthError(
            "Gnani rejected the API key or scope. Verify GNANI_API_KEY and account credits.",
            retryable=False,
        )
    if status == 429:
        return ProviderRateLimitError(
            "Gnani rate limit reached. Wait and retry with backoff.", retryable=True
        )
    if status >= 500:
        return ProviderUnavailableError(
            f"Gnani is temporarily unavailable (HTTP {status}). {message}".strip(),
            retryable=True,
        )
    return ProviderResponseError(
        f"Gnani rejected the request (HTTP {status}). {message}".strip(),
        retryable=False,
    )


def normalize_gnani_transport_error(exc: Exception) -> Exception:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderTimeoutError("Gnani request timed out.", retryable=True)
    return ProviderUnavailableError("Could not reach Gnani.", retryable=True)


def _extract_message(response: httpx.Response) -> str:
    try:
        body: Any = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        detail = body.get("detail")
        if isinstance(detail, dict) and detail.get("message"):
            return str(detail["message"])
        if body.get("message"):
            return str(body["message"])
    return ""
