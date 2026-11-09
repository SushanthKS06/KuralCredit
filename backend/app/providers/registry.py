from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.providers.adapters.local_reasoning_adapter import LocalTestReasoningAdapter
from app.providers.adapters.mock_providers import MockSTTProvider, MockTTSProvider
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.gnani.stt import GnaniSTTProvider
from app.providers.gnani.tts import GnaniTTSProvider
from app.providers.groq.reasoning import GroqReasoningProvider
from app.providers.interfaces import (
    ReasoningProvider,
    SpeechToTextProvider,
    TextToSpeechProvider,
)


@lru_cache
def get_catalog() -> CapabilityCatalog:
    return CapabilityCatalog.load(get_settings().capability_catalog_file)


class ProviderRegistry:
    def __init__(self, settings: Settings, catalog: CapabilityCatalog) -> None:
        self.settings = settings
        self.catalog = catalog
        self._stt: SpeechToTextProvider | None = None
        self._tts: TextToSpeechProvider | None = None
        self._reasoning: ReasoningProvider | None = None

    @property
    def stt(self) -> SpeechToTextProvider:
        if self._stt is None:
            if self.settings.is_mock_mode:
                self._stt = MockSTTProvider()
            else:
                self._stt = GnaniSTTProvider(self.settings, self.catalog)
        return self._stt

    @property
    def tts(self) -> TextToSpeechProvider:
        if self._tts is None:
            if self.settings.is_mock_mode:
                self._tts = MockTTSProvider(self.catalog, self.settings.gnani_tts_model)
            else:
                self._tts = GnaniTTSProvider(self.settings, self.catalog)
        return self._tts

    @property
    def reasoning(self) -> ReasoningProvider:
        if self._reasoning is None:
            if self.settings.is_mock_mode:
                self._reasoning = LocalTestReasoningAdapter()
            else:
                self._reasoning = GroqReasoningProvider(self.settings)
        return self._reasoning

    def health(self) -> dict[str, object]:
        mock_mode = self.settings.is_mock_mode
        return {
            "provider_mode": self.settings.provider_mode,
            "mock_mode": mock_mode,
            "live_provider_calls": not mock_mode,
            "stt_provider": self.stt.name,
            "tts_provider": self.tts.name,
            "reasoning_provider": self.reasoning.name,
            "gnani_configured": self.settings.gnani_configured,
            "gnani_stt_configured": self.settings.gnani_configured
            and self.settings.gnani_stt_enabled,
            "gnani_tts_configured": self.settings.gnani_configured
            and self.settings.gnani_tts_enabled,
            "groq_configured": self.settings.groq_configured,
            "stt_model": self.settings.gnani_stt_model,
            "tts_model": self.settings.gnani_tts_model,
            "reasoning_model": self.settings.groq_model,
            "capability_catalog_version": self.catalog.version,
        }


@lru_cache
def get_registry() -> ProviderRegistry:
    return ProviderRegistry(get_settings(), get_catalog())


def reset_registry() -> None:
    get_registry.cache_clear()
    get_catalog.cache_clear()
    get_settings.cache_clear()
