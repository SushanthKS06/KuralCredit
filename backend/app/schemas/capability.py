from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceOut(BaseModel):
    name: str
    gender: str
    model: str
    languages: list[str]
    persona: str | None = None
    description: str | None = None


class LanguageOut(BaseModel):
    code: str
    name: str
    native_name: str
    script: str
    stt_supported: bool
    voices: list[VoiceOut] = Field(default_factory=list)


class ProviderStatusOut(BaseModel):
    provider_mode: str
    mock_mode: bool
    live_provider_calls: bool
    stt_provider: str
    tts_provider: str
    reasoning_provider: str
    gnani_stt_configured: bool
    gnani_tts_configured: bool
    groq_configured: bool


class DefaultsOut(BaseModel):
    language: str
    voice: str
    stt_model: str
    tts_model: str


class CapabilitiesOut(BaseModel):
    catalog_version: str
    verified_at: str
    source_urls: list[str]
    stt_max_audio_seconds: int
    stt_supported_formats: list[str]
    stt_max_upload_bytes: int
    tts_supported_formats: list[str]
    languages: list[LanguageOut]
    defaults: DefaultsOut
    providers: ProviderStatusOut
    features: dict[str, bool]
    enabled_workflows: list[str] = Field(default_factory=list)
