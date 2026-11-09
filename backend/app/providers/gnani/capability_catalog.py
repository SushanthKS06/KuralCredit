from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, model_validator

from app.core.exceptions import ValidationAppError
from app.schemas.capability import LanguageOut, VoiceOut


class SttModelInfo(BaseModel):
    max_audio_seconds: int
    formats: list[str]
    auto_language: str | None = None


class SttLanguage(BaseModel):
    code: str
    name: str
    native_name: str
    script: str


class SttCatalog(BaseModel):
    models: dict[str, SttModelInfo]
    languages: list[SttLanguage]

    @model_validator(mode="after")
    def unique_languages(self) -> SttCatalog:
        codes = [language.code for language in self.languages]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate STT language codes in capability catalogue")
        return self


class TtsLanguage(BaseModel):
    code: str
    name: str


class VoiceEntry(BaseModel):
    name: str
    gender: str
    preferred_language: str | None = None
    persona: str | None = None
    description: str | None = None


class TtsModelInfo(BaseModel):
    all_languages: bool
    audio_tags: bool
    response_formats: list[str] = ["wav"]


class TtsCatalog(BaseModel):
    models: dict[str, TtsModelInfo]
    languages: list[TtsLanguage]
    voices_v2_5: list[VoiceEntry]
    voices_v3_0: list[VoiceEntry]
    all_language_codes: list[str]

    @model_validator(mode="after")
    def validate_voices(self) -> TtsCatalog:
        languages = {language.code for language in self.languages}
        names = [voice.name for voice in self.voices_v2_5]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate Timbre v2.5 voice names")
        v3_names = [voice.name for voice in self.voices_v3_0]
        if len(v3_names) != len(set(v3_names)):
            raise ValueError("Duplicate Timbre v3.0 voice names")
        for voice in self.voices_v2_5:
            if not voice.preferred_language or voice.preferred_language not in languages:
                raise ValueError(f"Voice {voice.name} has an unknown preferred language")
        for code in self.all_language_codes:
            if code not in languages:
                raise ValueError(f"v3.0 language {code} is missing from TTS languages")
        return self


class CatalogDocument(BaseModel):
    version: str
    verified_at: str
    source_urls: list[str]
    stt: SttCatalog
    tts: TtsCatalog


class CapabilityCatalog:
    def __init__(self, document: CatalogDocument) -> None:
        self.document = document

    @classmethod
    def load(cls, path: Path | str) -> CapabilityCatalog:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Capability catalogue not found at {path}")
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return cls(CatalogDocument.model_validate(raw))

    @property
    def version(self) -> str:
        return self.document.version

    @property
    def verified_at(self) -> str:
        return self.document.verified_at

    @property
    def source_urls(self) -> list[str]:
        return self.document.source_urls

    def stt_language(self, code: str) -> SttLanguage | None:
        return next((item for item in self.document.stt.languages if item.code == code), None)

    def stt_languages(self) -> list[SttLanguage]:
        return list(self.document.stt.languages)

    def stt_model(self, model: str) -> SttModelInfo:
        info = self.document.stt.models.get(model)
        if info is None:
            raise ValidationAppError(f"Unknown STT model: {model}")
        return info

    def validate_stt_language(self, language: str, model: str) -> str:
        info = self.stt_model(model)
        if info.auto_language and language == info.auto_language:
            return language
        if self.stt_language(language) is None:
            raise ValidationAppError(f"Language '{language}' is not supported by Gnani Prisma")
        return language

    def audio_formats(self, model: str) -> list[str]:
        return list(self.stt_model(model).formats)

    def max_audio_seconds(self, model: str) -> int:
        return self.stt_model(model).max_audio_seconds

    def tts_language_codes(self) -> list[str]:
        return [language.code for language in self.document.tts.languages]

    def tts_model(self, model: str) -> TtsModelInfo:
        info = self.document.tts.models.get(model)
        if info is None:
            raise ValidationAppError(f"Unknown TTS model: {model}")
        return info

    def tts_response_formats(self, model: str) -> list[str]:
        return list(self.tts_model(model).response_formats)

    def voices_for(self, language: str, model: str) -> list[VoiceEntry]:
        self.tts_model(model)
        if model == "timbre-v2.5":
            return [
                voice
                for voice in self.document.tts.voices_v2_5
                if voice.preferred_language == language
            ]
        if language not in self.document.tts.all_language_codes:
            return []
        return list(self.document.tts.voices_v3_0)

    def default_voice(self, language: str, model: str) -> str | None:
        voices = self.voices_for(language, model)
        return voices[0].name if voices else None

    def validate_voice(self, language: str, voice: str, model: str) -> None:
        if language not in self.tts_language_codes():
            raise ValidationAppError(f"Language '{language}' is not supported by Gnani Timbre")
        info = self.tts_model(model)
        if model == "timbre-v2.5":
            supported = self.voices_for(language, model)
            if not any(entry.name == voice for entry in supported):
                raise ValidationAppError(
                    f"Voice '{voice}' is not available for language '{language}' with {model}"
                )
            return
        if not info.all_languages:
            raise ValidationAppError(f"Model {model} does not support all languages")
        if language not in self.document.tts.all_language_codes:
            raise ValidationAppError(
                f"Voice '{voice}' does not support language '{language}' with {model}"
            )
        if not any(entry.name == voice for entry in self.document.tts.voices_v3_0):
            raise ValidationAppError(f"Voice '{voice}' is not part of the {model} catalogue")

    def languages_out(self, tts_model: str, stt_model: str) -> list[LanguageOut]:
        stt_codes = {language.code for language in self.document.stt.languages}
        result: list[LanguageOut] = []
        for language in self.document.stt.languages:
            voices = self.voices_for(language.code, tts_model)
            result.append(
                LanguageOut(
                    code=language.code,
                    name=language.name,
                    native_name=language.native_name,
                    script=language.script,
                    stt_supported=True,
                    voices=[
                        VoiceOut(
                            name=voice.name,
                            gender=voice.gender,
                            model=tts_model,
                            languages=[language.code],
                            persona=voice.persona,
                            description=voice.description,
                        )
                        for voice in voices
                    ],
                )
            )
        for language in self.document.tts.languages:
            if language.code in stt_codes:
                continue
            voices = self.voices_for(language.code, tts_model)
            result.append(
                LanguageOut(
                    code=language.code,
                    name=language.name,
                    native_name=language.name,
                    script="Latin",
                    stt_supported=False,
                    voices=[
                        VoiceOut(
                            name=voice.name,
                            gender=voice.gender,
                            model=tts_model,
                            languages=[language.code],
                            persona=voice.persona,
                            description=voice.description,
                        )
                        for voice in voices
                    ],
                )
            )
        return result
