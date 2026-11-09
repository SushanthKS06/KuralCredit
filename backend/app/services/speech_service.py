from __future__ import annotations

import io
import wave

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError, ValidationAppError
from app.models.application import Application
from app.observability.metrics import metrics
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.interfaces import SynthesisResult
from app.providers.registry import ProviderRegistry
from app.schemas.speech import SpeechStatusResponse, TranscribeResponse
from app.services.audit_service import AuditService
from app.storage.file_validation import validate_audio


class SpeechService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        registry: ProviderRegistry,
        catalog: CapabilityCatalog,
    ) -> None:
        self.db = db
        self.settings = settings
        self.registry = registry
        self.catalog = catalog
        self.audit = AuditService(db)

    def status(self) -> SpeechStatusResponse:
        health = self.registry.health()
        return SpeechStatusResponse(
            stt_available=bool(health.get("gnani_stt_configured")),
            tts_available=bool(health.get("gnani_tts_configured")),
            provider=str(health.get("stt_provider")),
            supported_audio_formats=self.catalog.audio_formats(self.settings.gnani_stt_model),
            max_audio_seconds=self.catalog.max_audio_seconds(self.settings.gnani_stt_model),
        )

    def transcribe(
        self,
        application: Application,
        *,
        audio: bytes,
        filename: str,
        content_type: str,
        language: str | None,
        actor: str,
    ) -> TranscribeResponse:
        selected_language = language or application.language
        if selected_language != application.language:
            raise ValidationAppError(
                "The transcription language must match the application language"
            )
        suffix = validate_audio(
            filename,
            audio,
            content_type,
            max_size_bytes=self.settings.max_audio_upload_size_mb * 1024 * 1024,
        )
        max_seconds = self.catalog.max_audio_seconds(self.settings.gnani_stt_model)
        duration = self._wav_duration_seconds(audio) if suffix == ".wav" else None
        if duration is not None and duration > max_seconds:
            raise ValidationAppError(
                f"Audio is {duration:.1f} seconds; the provider accepts at most "
                f"{max_seconds} seconds"
            )
        try:
            result = self.registry.stt.transcribe(
                audio=audio,
                filename=filename,
                content_type=content_type or "application/octet-stream",
                language=selected_language,
            )
        except AppError as exc:
            metrics.record_provider_call(
                self.registry.stt.name,
                "stt",
                latency_ms=0.0,
                success=False,
                error_code=exc.code,
            )
            raise
        metrics.record_provider_call(result.provider, "stt", result.latency_ms, success=True)
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="speech_transcribed",
            summary="Audio was transcribed. Transcript content is not written to logs.",
            detail={
                "provider": result.provider,
                "model": result.model,
                "request_id": result.request_id,
                "latency_ms": result.latency_ms,
                "detected_language": result.detected_language,
                "audio_bytes": len(audio),
            },
        )
        self.db.commit()
        return TranscribeResponse(
            transcript=result.transcript,
            language=selected_language,
            detected_language=result.detected_language,
            provider=result.provider,
            model=result.model,
            request_id=result.request_id,
            latency_ms=result.latency_ms,
            note="Review and correct the transcript before saving it.",
        )

    def synthesize(
        self,
        application: Application,
        *,
        text: str,
        language: str | None,
        voice: str | None,
        actor: str,
    ) -> SynthesisResult:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValidationAppError("Text is required for speech synthesis")
        if len(cleaned_text) > 1200:
            raise ValidationAppError("Speech synthesis text must be at most 1200 characters")
        selected_language = language or application.language
        selected_voice = voice or application.voice
        if selected_language != application.language:
            raise ValidationAppError("The speech language must match the application language")
        self.catalog.validate_voice(
            selected_language, selected_voice, self.settings.gnani_tts_model
        )
        try:
            result = self.registry.tts.synthesize(
                text=cleaned_text,
                language=selected_language,
                voice=selected_voice,
            )
        except AppError as exc:
            metrics.record_provider_call(
                self.registry.tts.name,
                "tts",
                latency_ms=0.0,
                success=False,
                error_code=exc.code,
            )
            raise
        metrics.record_provider_call(result.provider, "tts", result.latency_ms, success=True)
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="speech_synthesized",
            summary="Prompt audio was synthesized. Text content is not written to logs.",
            detail={
                "provider": result.provider,
                "model": result.model,
                "request_id": result.request_id,
                "latency_ms": result.latency_ms,
                "characters": len(text),
                "voice": selected_voice,
                "language": selected_language,
            },
        )
        self.db.commit()
        return result

    @staticmethod
    def _wav_duration_seconds(audio: bytes) -> float | None:
        try:
            with wave.open(io.BytesIO(audio), "rb") as handle:
                frames = handle.getnframes()
                rate = handle.getframerate()
                if rate <= 0:
                    return None
                return frames / float(rate)
        except (wave.Error, EOFError):
            return None
