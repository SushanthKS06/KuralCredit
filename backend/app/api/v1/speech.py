from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import (
    enforce_rate_limit,
    get_catalog_dep,
    get_db_dep,
    get_registry_dep,
    get_settings_dep,
    require_applicant,
)
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models.application import Application
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.registry import ProviderRegistry
from app.repositories.application_repository import ApplicationRepository
from app.schemas.speech import (
    SpeechStatusResponse,
    SynthesizeRequest,
    TranscribeResponse,
)
from app.services.session_service import SessionContext
from app.services.speech_service import SpeechService

router = APIRouter(prefix="/speech", tags=["speech"])


def _owned_application(application_id: str, session: SessionContext, db: Session) -> Application:
    if session.application_id != application_id:
        raise ForbiddenError("You can only use speech for your own application")
    application = ApplicationRepository(db).get(application_id)
    if application is None:
        raise NotFoundError("Application not found")
    return application


@router.get("/status", response_model=SpeechStatusResponse)
def speech_status(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
    catalog: CapabilityCatalog = Depends(get_catalog_dep),
) -> SpeechStatusResponse:
    return SpeechService(db, settings, registry, catalog).status()


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    application_id: str = Form(...),
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
    session: SessionContext = Depends(require_applicant),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
    catalog: CapabilityCatalog = Depends(get_catalog_dep),
) -> TranscribeResponse:
    enforce_rate_limit("transcribe", session, settings)
    application = _owned_application(application_id, session, db)
    max_bytes = settings.max_audio_upload_size_mb * 1024 * 1024
    content = await audio.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValidationAppError(
            f"Audio exceeds the configured limit of {settings.max_audio_upload_size_mb} MB"
        )
    filename = audio.filename or "recording.wav"
    if not Path(filename).suffix:
        filename = f"{filename}.wav"
    service = SpeechService(db, settings, registry, catalog)
    return service.transcribe(
        application,
        audio=content,
        filename=filename,
        content_type=audio.content_type or "application/octet-stream",
        language=language,
        actor=f"applicant:{application.id}",
    )


@router.post("/synthesize")
def synthesize(
    payload: SynthesizeRequest,
    session: SessionContext = Depends(require_applicant),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
    catalog: CapabilityCatalog = Depends(get_catalog_dep),
) -> Response:
    enforce_rate_limit("synthesize", session, settings)
    application = _owned_application(payload.application_id, session, db)
    result = SpeechService(db, settings, registry, catalog).synthesize(
        application,
        text=payload.text,
        language=payload.language,
        voice=payload.voice,
        actor=f"applicant:{application.id}",
    )
    extension = {
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
        "audio/flac": "flac",
        "audio/aac": "aac",
        "audio/mp4": "m4a",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
    }.get(result.content_type, "wav")
    headers = {
        "Content-Disposition": f'inline; filename="kuralcredit-prompt.{extension}"',
        "Cache-Control": "no-store",
        "X-Provider": result.provider,
        "X-Model": result.model,
        "X-Latency-Ms": f"{result.latency_ms:.2f}",
    }
    if result.request_id:
        headers["X-Provider-Request-Id"] = result.request_id
    return Response(
        content=result.audio,
        media_type=result.content_type or "audio/wav",
        headers=headers,
    )
