from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_catalog_dep, get_registry_dep, get_settings_dep
from app.core.config import Settings
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.registry import ProviderRegistry
from app.schemas.capability import (
    CapabilitiesOut,
    DefaultsOut,
    ProviderStatusOut,
)

router = APIRouter(tags=["capabilities"])


@router.get("/capabilities", response_model=CapabilitiesOut)
def capabilities(
    settings: Settings = Depends(get_settings_dep),
    catalog: CapabilityCatalog = Depends(get_catalog_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
) -> CapabilitiesOut:
    health = registry.health()
    return CapabilitiesOut(
        catalog_version=catalog.version,
        verified_at=catalog.verified_at,
        source_urls=catalog.source_urls,
        stt_max_audio_seconds=catalog.max_audio_seconds(settings.gnani_stt_model),
        stt_supported_formats=catalog.audio_formats(settings.gnani_stt_model),
        stt_max_upload_bytes=settings.max_audio_upload_size_bytes,
        tts_supported_formats=catalog.tts_response_formats(settings.gnani_tts_model),
        languages=catalog.languages_out(settings.gnani_tts_model, settings.gnani_stt_model),
        defaults=DefaultsOut(
            language=settings.gnani_default_language,
            voice=settings.gnani_default_voice,
            stt_model=settings.gnani_stt_model,
            tts_model=settings.gnani_tts_model,
        ),
        providers=ProviderStatusOut(
            provider_mode=str(health.get("provider_mode")),
            mock_mode=bool(health.get("mock_mode")),
            live_provider_calls=bool(health.get("live_provider_calls")),
            stt_provider=str(health.get("stt_provider")),
            tts_provider=str(health.get("tts_provider")),
            reasoning_provider=str(health.get("reasoning_provider")),
            gnani_stt_configured=bool(health.get("gnani_stt_configured")),
            gnani_tts_configured=bool(health.get("gnani_tts_configured")),
            groq_configured=bool(health.get("groq_configured")),
        ),
        features={
            "voice_input": True,
            "voice_output": True,
            "text_fallback": True,
            "document_upload": True,
            "reviewer_workflow": True,
            "json_export": True,
            "reviewer_login": settings.reviewer_login_configured,
            "mock_provider_mode": settings.is_mock_mode,
        },
        enabled_workflows=["loan_application", "customer_support_intake"],
    )
