from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAPABILITY_CATALOG = REPO_ROOT / "backend" / "app" / "config" / "capabilities.json"
PLACEHOLDER_SECRETS = {
    "",
    "replace-with-a-long-random-string",
    "dev-only-local-secret-change-before-any-deployment",
}


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if str(item).strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "KuralCredit"
    app_base_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:5173"
    backend_public_url: str = "http://localhost:8000"
    secret_key: str = "dev-only-local-secret-change-before-any-deployment"
    database_url: str = "sqlite:///./kuralcredit.db"

    # "real" calls the configured providers. "mock" is an explicit,
    # deterministic demo/test mode and is rejected in production.
    provider_mode: Literal["real", "mock"] = "real"

    gnani_api_key: SecretStr | None = None
    gnani_api_base_url: str = "https://api.vachana.ai"
    gnani_stt_enabled: bool = True
    gnani_tts_enabled: bool = True
    gnani_stt_timeout_seconds: float = Field(default=45.0, gt=0, le=180)
    gnani_tts_timeout_seconds: float = Field(default=45.0, gt=0, le=180)
    gnani_max_retries: int = Field(default=2, ge=0, le=5)
    gnani_default_language: str = "ta-IN"
    gnani_default_voice: str = "Trisha"
    gnani_tts_model: str = "timbre-v2.5"
    gnani_stt_model: str = "prisma-v3.0"
    gnani_stt_format: str = "transcribe"
    gnani_capability_catalog_path: str = str(DEFAULT_CAPABILITY_CATALOG)

    groq_api_key: SecretStr | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"
    groq_reasoning_effort: str = "low"
    groq_timeout_seconds: float = Field(default=45.0, gt=0, le=180)
    groq_max_retries: int = Field(default=2, ge=0, le=5)
    groq_max_output_tokens: int = Field(default=2048, ge=256, le=8192)
    groq_max_input_chars: int = Field(default=12000, ge=1000, le=60000)
    groq_strict_schema: bool = True

    upload_dir: Path = Path("./uploads")
    max_upload_size_mb: int = Field(default=10, ge=1, le=50)
    max_audio_upload_size_mb: int = Field(default=15, ge=1, le=50)
    allowed_document_types: str = "pdf,csv,xlsx"
    audio_retention_enabled: bool = False
    audio_retention_hours: int = Field(default=24, ge=1)
    document_retention_days: int = Field(default=30, ge=1)
    log_level: str = "INFO"
    log_redact_pii: bool = True
    rate_limit_per_minute: int = Field(default=30, ge=1, le=600)
    cors_allowed_origins: str = "http://localhost:5173"

    reviewer_demo_email: str = "reviewer@kuralcredit.demo"
    reviewer_demo_password: SecretStr | None = None
    reviewer_display_name: str = "Demo Reviewer"
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    reconciliation_tolerance_percent: Decimal = Field(default=Decimal("5"), ge=0, le=100)

    @field_validator("allowed_document_types")
    @classmethod
    def validate_document_types(cls, value: str) -> str:
        allowed = {"pdf", "csv", "xlsx"}
        parsed = {item.lower().lstrip(".") for item in _split_csv(value)}
        if not parsed:
            raise ValueError("ALLOWED_DOCUMENT_TYPES must not be empty")
        unknown = parsed - allowed
        if unknown:
            raise ValueError(f"Unsupported document types: {sorted(unknown)}")
        return ",".join(sorted(parsed))

    @field_validator("gnani_stt_model")
    @classmethod
    def validate_stt_model(cls, value: str) -> str:
        if value not in {"prisma-v2.5", "prisma-v3.0"}:
            raise ValueError("GNANI_STT_MODEL must be prisma-v2.5 or prisma-v3.0")
        return value

    @field_validator("gnani_tts_model")
    @classmethod
    def validate_tts_model(cls, value: str) -> str:
        if value not in {"timbre-v2.5", "timbre-v3.0"}:
            raise ValueError("GNANI_TTS_MODEL must be timbre-v2.5 or timbre-v3.0")
        return value

    @field_validator("gnani_stt_format")
    @classmethod
    def validate_stt_format(cls, value: str) -> str:
        if value not in {"transcribe", "verbatim", "codemix", "transliterate"}:
            raise ValueError("GNANI_STT_FORMAT is not a documented value")
        return value

    @field_validator("groq_reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, value: str) -> str:
        if value not in {"low", "medium", "high"}:
            raise ValueError("GROQ_REASONING_EFFORT must be low, medium or high")
        return value

    @model_validator(mode="after")
    def validate_provider_safety(self) -> Settings:
        if self.provider_mode == "real":
            if not self.gnani_configured:
                raise ValueError(
                    "GNANI_API_KEY is required in real provider mode; "
                    "set PROVIDER_MODE=mock for an explicitly labelled demo"
                )
            if not self.groq_configured:
                raise ValueError(
                    "GROQ_API_KEY is required in real provider mode; "
                    "set PROVIDER_MODE=mock for an explicitly labelled demo"
                )
        if self.app_env == "production":
            if self.provider_mode == "mock":
                raise ValueError(
                    "PROVIDER_MODE=mock is not allowed in production; use real providers"
                )
            if self.secret_key in PLACEHOLDER_SECRETS or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a strong non-placeholder value in production")
            if not self.reviewer_demo_password:
                raise ValueError("REVIEWER_DEMO_PASSWORD is required for the reviewer demo login")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_mock_mode(self) -> bool:
        return self.provider_mode == "mock"

    @property
    def cors_origins(self) -> list[str]:
        origins = _split_csv(self.cors_allowed_origins)
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins

    @property
    def allowed_document_suffixes(self) -> set[str]:
        return {f".{item}" for item in _split_csv(self.allowed_document_types)}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_audio_upload_size_bytes(self) -> int:
        return self.max_audio_upload_size_mb * 1024 * 1024

    @property
    def capability_catalog_file(self) -> Path:
        path = Path(self.gnani_capability_catalog_path)
        if path.is_absolute():
            return path
        candidate = (REPO_ROOT / path).resolve()
        if candidate.exists():
            return candidate
        return (Path.cwd() / path).resolve()

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if path.is_absolute():
            return path
        return (REPO_ROOT / path).resolve()

    @property
    def gnani_configured(self) -> bool:
        return bool(self.gnani_api_key and self.gnani_api_key.get_secret_value().strip())

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key.get_secret_value().strip())

    @property
    def reviewer_login_configured(self) -> bool:
        return bool(
            self.reviewer_demo_email
            and self.reviewer_demo_password
            and self.reviewer_demo_password.get_secret_value()
        )

    def redacted_diagnostics(self) -> dict[str, object]:
        def masked(value: SecretStr | None) -> str:
            if not value:
                return "not_set"
            raw = value.get_secret_value()
            if not raw:
                return "not_set"
            if len(raw) <= 4:
                return "set"
            return f"set(length={len(raw)})"

        return {
            "app_env": self.app_env,
            "provider_mode": self.provider_mode,
            "database_url_scheme": re.sub(r"://.*", "://<redacted>", self.database_url),
            "gnani_api_key": masked(self.gnani_api_key),
            "gnani_api_base_url": self.gnani_api_base_url,
            "gnani_stt_enabled": self.gnani_stt_enabled,
            "gnani_tts_enabled": self.gnani_tts_enabled,
            "gnani_stt_model": self.gnani_stt_model,
            "gnani_tts_model": self.gnani_tts_model,
            "groq_api_key": masked(self.groq_api_key),
            "groq_base_url": self.groq_base_url,
            "groq_model": self.groq_model,
            "upload_dir": str(self.upload_path),
            "max_upload_size_mb": self.max_upload_size_mb,
            "reviewer_login_configured": self.reviewer_login_configured,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "reconciliation_tolerance_percent": str(self.reconciliation_tolerance_percent),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
