from __future__ import annotations

import logging
import time
import uuid

import httpx

from app.core.config import Settings
from app.core.exceptions import ProviderAuthError
from app.providers.gnani.errors import (
    normalize_gnani_error,
    normalize_gnani_transport_error,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GnaniClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.gnani_api_base_url.rstrip("/")

    def api_key(self) -> str:
        if not self.settings.gnani_api_key:
            raise ProviderAuthError("GNANI_API_KEY is not configured")
        value = self.settings.gnani_api_key.get_secret_value().strip()
        if not value:
            raise ProviderAuthError("GNANI_API_KEY is not configured")
        return value

    def request(
        self,
        method: str,
        path: str,
        *,
        timeout: float,
        operation: str,
        **kwargs,
    ) -> tuple[httpx.Response, str, float]:
        request_id = uuid.uuid4().hex
        headers = dict(kwargs.pop("headers", {}))
        headers["X-API-Key-ID"] = self.api_key()
        headers["X-API-Request-ID"] = request_id
        attempts = self.settings.gnani_max_retries + 1
        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
                    response = client.request(method, path, headers=headers, **kwargs)
                if response.status_code in RETRYABLE_STATUS and attempt < attempts - 1:
                    time.sleep(min(0.5 * (2**attempt), 4.0))
                    continue
                latency_ms = (time.perf_counter() - started) * 1000
                if response.status_code >= 400:
                    raise normalize_gnani_error(response)
                return response, request_id, latency_ms
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(min(0.5 * (2**attempt), 4.0))
                    continue
                latency_ms = (time.perf_counter() - started) * 1000
                logger.warning(
                    "gnani_transport_failure",
                    extra={
                        "extra_fields": {
                            "operation": operation,
                            "latency_ms": round(latency_ms, 2),
                            "attempts": attempt + 1,
                        }
                    },
                )
                raise normalize_gnani_transport_error(exc) from exc
        if last_error is not None:
            raise normalize_gnani_transport_error(last_error)
        raise RuntimeError("Unreachable Gnani request state")
