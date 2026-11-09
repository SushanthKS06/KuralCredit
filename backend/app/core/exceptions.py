from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "application_error"

    def __init__(
        self,
        message: str,
        *,
        details: Any | None = None,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class InvalidStateTransition(ConflictError):
    code = "invalid_state_transition"


class ValidationAppError(AppError):
    status_code = 422
    code = "validation_error"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class ConfigurationError(AppError):
    status_code = 500
    code = "configuration_error"


class ProviderError(AppError):
    status_code = 502
    code = "provider_error"
    provider = "unknown"

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: Any | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.retryable = retryable


class ProviderAuthError(ProviderError):
    code = "provider_auth_error"


class ProviderRateLimitError(ProviderError):
    status_code = 503
    code = "provider_rate_limited"


class ProviderTimeoutError(ProviderError):
    status_code = 504
    code = "provider_timeout"


class ProviderUnavailableError(ProviderError):
    status_code = 503
    code = "provider_unavailable"


class ProviderResponseError(ProviderError):
    code = "provider_response_error"


class ProviderSchemaError(ProviderError):
    code = "provider_schema_error"
