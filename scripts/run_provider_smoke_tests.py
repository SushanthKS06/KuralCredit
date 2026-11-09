#!/usr/bin/env python3
"""Opt-in live smoke tests for Gnani Prisma STT, Gnani Timbre TTS, and Groq.

No external provider call is made unless ``--live`` is supplied. Results are
reported as PASS, FAIL, or BLOCKED so an unverified provider is never shown as
working. API key values are never printed.

Usage:
    python scripts/run_provider_smoke_tests.py
    python scripts/run_provider_smoke_tests.py --live
    python scripts/run_provider_smoke_tests.py --live --provider stt
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.fact_definitions import target_field_payload
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.gnani.stt import GnaniSTTProvider
from app.providers.gnani.tts import GnaniTTSProvider
from app.providers.groq.reasoning import GroqReasoningProvider

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

TEST_LANGUAGE = "en-IN"
TEST_VOICE = "Kaveri"
TEST_PHRASE = "Our annual sales last year were eighteen lakh rupees."


class BlockedError(RuntimeError):
    """The check cannot run safely or meaningfully in this environment."""


def _redact(message: str, settings: Settings) -> str:
    values = [
        settings.gnani_api_key.get_secret_value() if settings.gnani_api_key else "",
        settings.groq_api_key.get_secret_value() if settings.groq_api_key else "",
        settings.reviewer_demo_password.get_secret_value()
        if settings.reviewer_demo_password
        else "",
    ]
    redacted = message
    for value in values:
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted[:500]


def _safe_provider_name(value: object) -> str:
    return str(value) if value else "unknown"


def test_gnani_tts(settings: Settings, catalog: CapabilityCatalog) -> tuple[str, str]:
    provider = GnaniTTSProvider(settings, catalog)
    started = time.perf_counter()
    result = provider.synthesize(
        text=TEST_PHRASE,
        language=TEST_LANGUAGE,
        voice=TEST_VOICE,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not result.audio:
        raise AssertionError("Gnani Timbre returned empty audio")
    if len(result.audio) < 44:
        raise AssertionError("Gnani Timbre returned an implausibly small audio payload")
    return (
        PASS,
        f"audio_bytes={len(result.audio)}, content_type={result.content_type}, "
        f"provider={_safe_provider_name(result.provider)}, latency_ms={elapsed_ms:.0f}",
    )


def _synthesize_for_stt(settings: Settings, catalog: CapabilityCatalog) -> tuple[bytes, str]:
    provider = GnaniTTSProvider(settings, catalog)
    result = provider.synthesize(
        text=TEST_PHRASE,
        language=TEST_LANGUAGE,
        voice=TEST_VOICE,
    )
    if not result.audio:
        raise BlockedError("TTS prerequisite returned no audio for the STT round trip")
    return result.audio, result.content_type or "audio/wav"


def test_gnani_stt(
    settings: Settings,
    catalog: CapabilityCatalog,
    spoken_audio: bytes | None = None,
    content_type: str = "audio/wav",
) -> tuple[str, str]:
    if spoken_audio is None:
        try:
            spoken_audio, content_type = _synthesize_for_stt(settings, catalog)
        except BlockedError:
            raise
        except Exception as exc:
            raise BlockedError(
                f"STT round-trip needs a spoken sample from Timbre first: {exc}"
            ) from exc
    suffix = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
        "audio/flac": "flac",
        "audio/aac": "aac",
        "audio/mp4": "m4a",
    }.get(content_type.lower(), "wav")
    provider = GnaniSTTProvider(settings, catalog)
    started = time.perf_counter()
    result = provider.transcribe(
        audio=spoken_audio,
        filename=f"smoke_roundtrip.{suffix}",
        content_type=content_type,
        language=TEST_LANGUAGE,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not result.transcript.strip():
        raise AssertionError("Gnani Prisma returned an empty transcript")
    return (
        PASS,
        f"transcript_chars={len(result.transcript)}, "
        f"detected_language={result.detected_language}, "
        f"provider={_safe_provider_name(result.provider)}, latency_ms={elapsed_ms:.0f}",
    )


def test_groq_reasoning(settings: Settings) -> tuple[str, str]:
    provider = GroqReasoningProvider(settings)
    started = time.perf_counter()
    result = provider.extract_applicant_facts(
        transcript=(
            "Our last financial year sales were 18 lakh rupees and GST turnover was 16.5 lakh."
        ),
        target_fields=target_field_payload(["annual_sales", "gst_turnover"]),
        language=TEST_LANGUAGE,
        prior_facts=[],
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if result.provider != "groq":
        raise AssertionError(f"Unexpected reasoning provider: {result.provider}")
    facts = result.data.get("candidate_facts") or []
    if not facts:
        raise AssertionError("Groq returned no candidate facts for an explicit declaration")
    annual = [
        fact
        for fact in facts
        if fact.get("field_key") == "annual_sales"
        and str(fact.get("normalized_candidate", "")).startswith("1800000")
    ]
    if not annual:
        raise AssertionError("Groq did not extract the explicit 18 lakh annual sales value")
    return (
        PASS,
        f"candidate_facts={len(facts)}, model={result.model}, "
        f"schema_mode={result.schema_mode}, latency_ms={elapsed_ms:.0f}",
    )


def _run(
    name: str,
    check: Callable[[], tuple[str, str]],
    settings: Settings,
) -> str:
    print(f"\n--- {name} ---")
    try:
        status, detail = check()
    except BlockedError as exc:
        print(f"  [{BLOCKED}] {_redact(str(exc), settings)}")
        return BLOCKED
    except AppError as exc:
        print(f"  [{FAIL}] {exc.__class__.__name__}: {_redact(str(exc), settings)}")
        return FAIL
    except Exception as exc:
        print(f"  [{FAIL}] {exc.__class__.__name__}: {_redact(str(exc), settings)}")
        return FAIL
    print(f"  [{status}] {detail}")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run opt-in live provider smoke tests (no key values are printed)."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly allow real Gnani and Groq network calls.",
    )
    parser.add_argument(
        "--provider",
        choices=("all", "stt", "tts", "groq"),
        default="all",
        help="Provider check to run (default: all).",
    )
    args = parser.parse_args()

    selected = ["stt", "tts", "groq"] if args.provider == "all" else [args.provider]

    print("=" * 66)
    print("  KuralCredit Provider Smoke Tests")
    print("=" * 66)

    if not args.live:
        print("\nLive calls are disabled by default. No provider was contacted.")
        print("Re-run with --live after rotating any previously exposed credentials.")
        for name in selected:
            print(f"\n--- {name.upper()} ---")
            print(f"  [{BLOCKED}] --live was not supplied")
        print("\n[SUMMARY] BLOCKED - live providers were not verified.")
        return 2

    try:
        settings = Settings()
    except Exception as exc:
        print(f"\n[{BLOCKED}] Configuration is not safe for live tests: {exc}")
        print("\n[SUMMARY] BLOCKED - live providers were not verified.")
        return 2

    if settings.is_mock_mode:
        print("\n[BLOCKED] PROVIDER_MODE=mock; switch to real mode to test live providers.")
        print("\n[SUMMARY] BLOCKED - live providers were not verified.")
        return 2

    catalog = CapabilityCatalog.load(settings.capability_catalog_file)

    results: dict[str, str] = {}
    spoken_audio: bytes | None = None
    spoken_content_type = "audio/wav"

    if "tts" in selected:
        results["tts"] = _run(
            "Gnani Timbre TTS",
            lambda: test_gnani_tts(settings, catalog),
            settings,
        )
        if results["tts"] == PASS:
            try:
                spoken_audio, spoken_content_type = _synthesize_for_stt(settings, catalog)
            except Exception as exc:
                print(f"  [WARN] Could not retain TTS audio for STT: {_redact(str(exc), settings)}")

    if "stt" in selected:
        results["stt"] = _run(
            "Gnani Prisma STT",
            lambda: test_gnani_stt(settings, catalog, spoken_audio, spoken_content_type),
            settings,
        )

    if "groq" in selected:
        results["groq"] = _run("Groq GPT-OSS 120B", lambda: test_groq_reasoning(settings), settings)

    print("\n" + "=" * 66)
    for name in selected:
        print(f"  {name.upper():<6} {results.get(name, BLOCKED)}")

    if FAIL in results.values():
        print("  [SUMMARY] FAIL - at least one live provider check failed.")
        return 1
    if BLOCKED in results.values():
        print("  [SUMMARY] BLOCKED - at least one live provider check could not run.")
        return 2
    print("  [SUMMARY] PASS - all selected live provider checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
