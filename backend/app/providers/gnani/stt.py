from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.exceptions import ProviderResponseError, ValidationAppError
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.gnani.client import GnaniClient
from app.providers.gnani.schemas import GnaniTranscriptionResponse
from app.providers.interfaces import SpeechToTextProvider, TranscriptionResult

logger = logging.getLogger(__name__)


class GnaniSTTProvider(SpeechToTextProvider):
    name = "gnani-prisma"

    def __init__(self, settings: Settings, catalog: CapabilityCatalog) -> None:
        self.settings = settings
        self.catalog = catalog
        self.client = GnaniClient(settings)

    def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        language: str,
    ) -> TranscriptionResult:
        if not audio:
            raise ValidationAppError("Audio file is empty")
        if not self.settings.gnani_stt_enabled:
            raise ProviderResponseError("Gnani STT is disabled by configuration")
        model = self.settings.gnani_stt_model
        language_code = self.catalog.validate_stt_language(language, model)
        data: dict[str, str] = {
            "language_code": language_code,
            "model": model,
        }
        if model == "prisma-v3.0":
            data["format"] = self.settings.gnani_stt_format
        files = {"audio_file": (filename, audio, content_type)}
        response, request_id, latency_ms = self.client.request(
            "POST",
            "/stt/v3",
            timeout=self.settings.gnani_stt_timeout_seconds,
            operation="stt",
            data=data,
            files=files,
        )
        try:
            payload = GnaniTranscriptionResponse.model_validate(response.json())
        except ValueError as exc:
            raise ProviderResponseError("Gnani returned an unexpected STT response") from exc
        if not payload.success:
            raise ProviderResponseError("Gnani could not transcribe the audio")
        return TranscriptionResult(
            transcript=payload.transcript.strip(),
            language=language_code,
            detected_language=payload.detected_language_code,
            model=payload.model or model,
            provider=self.name,
            request_id=payload.request_id or request_id,
            latency_ms=round(latency_ms, 2),
            raw_metadata={
                "processing_time": payload.processing_time,
                "end_to_end_latency": payload.end_to_end_latency,
            },
        )
