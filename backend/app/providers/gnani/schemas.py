from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GnaniTranscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    request_id: str | None = None
    transcript: str = ""
    model: str | None = None
    detected_language_code: str | None = None
    processing_time: float | None = None
    end_to_end_latency: float | None = None
    output: dict[str, Any] | None = None


class GnaniErrorDetail(BaseModel):
    type: str | None = None
    message: str | None = None


class GnaniErrorResponse(BaseModel):
    success: bool = False
    error: GnaniErrorDetail | None = None
    request_id: str | None = None


class GnaniTTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str
    model: str
    language: str
    speed: float = 1.0
    audio_config: dict[str, Any] = Field(
        default_factory=lambda: {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        }
    )
