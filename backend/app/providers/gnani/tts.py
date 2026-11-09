from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import ProviderResponseError
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.gnani.client import GnaniClient
from app.providers.gnani.schemas import GnaniTTSRequest
from app.providers.interfaces import SynthesisResult, TextToSpeechProvider


class GnaniTTSProvider(TextToSpeechProvider):
    name = "gnani-timbre"

    def __init__(self, settings: Settings, catalog: CapabilityCatalog) -> None:
        self.settings = settings
        self.catalog = catalog
        self.client = GnaniClient(settings)

    def synthesize(self, text: str, language: str, voice: str) -> SynthesisResult:
        if not self.settings.gnani_tts_enabled:
            raise ProviderResponseError("Gnani TTS is disabled by configuration")
        model = self.settings.gnani_tts_model
        self.catalog.validate_voice(language, voice, model)
        body = GnaniTTSRequest(
            text=text,
            voice=voice,
            model=model,
            language=language,
        ).model_dump()
        response, request_id, latency_ms = self.client.request(
            "POST",
            "/api/v1/tts/inference",
            timeout=self.settings.gnani_tts_timeout_seconds,
            operation="tts",
            json=body,
            headers={"Content-Type": "application/json"},
        )
        content_type = response.headers.get("content-type", "audio/wav").split(";")[0].strip()
        audio = response.content
        if not audio:
            raise ProviderResponseError("Gnani returned empty audio")
        if content_type.startswith("application/json"):
            raise ProviderResponseError("Gnani returned an error instead of audio")
        return SynthesisResult(
            audio=audio,
            content_type=content_type,
            model=model,
            provider=self.name,
            latency_ms=round(latency_ms, 2),
            request_id=request_id,
            raw_metadata={"voice": voice, "language": language},
        )
