from __future__ import annotations

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    transcript: str
    language: str
    detected_language: str | None = None
    provider: str
    model: str
    request_id: str | None = None
    latency_ms: float
    note: str | None = None


class SynthesizeRequest(BaseModel):
    application_id: str
    text: str = Field(min_length=1, max_length=1200)
    language: str | None = None
    voice: str | None = None


class SpeechStatusResponse(BaseModel):
    stt_available: bool
    tts_available: bool
    provider: str
    supported_audio_formats: list[str]
    max_audio_seconds: int
