"""Explicit deterministic mock speech providers.

These providers are used only when PROVIDER_MODE=mock. They are intentionally
labelled with mock-* names so logs, capabilities, and the UI can state clearly
that no live Gnani call occurred. Real mode never falls back to these classes.
"""

from __future__ import annotations

import io
import json
import math
import struct
import time
import wave
from pathlib import Path

from app.core.exceptions import ValidationAppError
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.interfaces import (
    SpeechToTextProvider,
    SynthesisResult,
    TextToSpeechProvider,
    TranscriptionResult,
)

DEFAULT_TRANSCRIPTS = {
    "en-IN": (
        "My business is a textile shop. Last year sales were 18 lakh rupees. "
        "GST turnover was 16 lakh 50 thousand."
    ),
    "ta-IN": (
        "En kadai oru thunikkadai. Kadaandha aandu sales 18 lakh rubai. "
        "GST turnover 16 lakh 50 thousand."
    ),
    "hi-IN": (
        "Meri dukaan kapde bechti hai. Pichhle saal ki sales 18 lakh rupaye thi. "
        "GST turnover 16 lakh 50 thousand tha."
    ),
}


def _load_transcripts() -> dict[str, str]:
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "mock_transcripts.json"
    if fixture.exists():
        try:
            data = json.loads(fixture.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                return {str(key): str(value) for key, value in data.items()}
        except (OSError, ValueError):
            pass
    return dict(DEFAULT_TRANSCRIPTS)


def _tone_wav(duration_seconds: float = 0.45, sample_rate: int = 16000) -> bytes:
    frames = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            amplitude = int(900 * math.sin(2 * math.pi * 440 * index / sample_rate))
            handle.writeframesraw(struct.pack("<h", amplitude))
    return buffer.getvalue()


class MockSTTProvider(SpeechToTextProvider):
    name = "mock-gnani-prisma"

    def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        language: str,
    ) -> TranscriptionResult:
        if not audio:
            raise ValidationAppError("Audio file is empty")
        transcripts = _load_transcripts()
        if language not in transcripts:
            raise ValidationAppError(
                f"No deterministic mock transcript is configured for language '{language}'"
            )
        return TranscriptionResult(
            transcript=transcripts[language],
            language=language,
            detected_language=language,
            model="mock-prisma",
            provider=self.name,
            request_id="mock-stt",
            latency_ms=1.0,
            raw_metadata={"mock": True, "live_provider": False},
        )


class MockTTSProvider(TextToSpeechProvider):
    name = "mock-gnani-timbre"

    def __init__(self, catalog: CapabilityCatalog, tts_model: str) -> None:
        self.catalog = catalog
        self.tts_model = tts_model

    def synthesize(self, text: str, language: str, voice: str) -> SynthesisResult:
        if not text.strip():
            raise ValidationAppError("Text is required for synthesis")
        self.catalog.validate_voice(language, voice, self.tts_model)
        started = time.perf_counter()
        return SynthesisResult(
            audio=_tone_wav(),
            content_type="audio/wav",
            model="mock-timbre",
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            request_id="mock-tts",
            raw_metadata={"mock": True, "live_provider": False},
        )
