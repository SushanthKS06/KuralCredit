# KuralCredit — Gnani Prisma STT & Timbre TTS Integration Guide

## 1. Overview
KuralCredit utilizes Gnani's speech layer for:
- **Gnani Prisma STT**: Converts applicant spoken audio (Tamil, Tanglish, English) into text transcripts.
- **Gnani Timbre TTS**: Synthesizes clarification questions and conversational prompts into natural, high-fidelity Indian-language speech.

All Gnani API calls originate exclusively from the backend (`backend/app/providers/gnani/`). The frontend never accesses Gnani credentials.

### Provider mode and live status

- `PROVIDER_MODE=real`: uses the configured Gnani adapters. Missing keys
  fail validation, and provider failures surface to the caller.
- `PROVIDER_MODE=mock`: uses deterministic, clearly labelled mock
  adapters for tests and offline demos. Mock mode is rejected in
  production.
- Real and mock providers are never selected silently at runtime.
- Live Gnani verification is **BLOCKED** in the current environment until
  the exposed credentials are rotated. The request/response contracts
  below are configuration references, not evidence of a successful live
  call.

---

## 2. Configured Provider Endpoints & Contracts

### A. Prisma STT
- **Base URL**: `https://api.vachana.ai`
- **Path**: `POST /stt/v3`
- **Authentication**: `X-API-Key-ID: <GNANI_API_KEY>`
- **Request Format**: `multipart/form-data`
  - `audio_file`: binary audio data (16kHz mono WAV or PCM)
  - `language_code`: e.g. `ta-IN`, `en-IN`, `hi-IN`
  - `model`: `prisma-v3.0`
  - `format`: `wav`
- **Response Format**: `application/json`
  ```json
  {
    "success": true,
    "transcript": "எங்க கடை சென்ற வருட விற்பனை பதினெட்டு லட்சம் ரூபாய்.",
    "detected_language_code": "ta-IN",
    "model": "prisma-v3.0",
    "request_id": "gnani-stt-99210",
    "processing_time": 0.32,
    "end_to_end_latency": 0.45
  }
  ```

### B. Timbre TTS
- **Base URL**: `https://api.vachana.ai`
- **Path**: `POST /api/v1/tts/inference`
- **Authentication**: `X-API-Key-ID: <GNANI_API_KEY>`
- **Request Format**: `application/json`
  ```json
  {
    "text": "வணக்கம், குரல் கிரெடிட் உங்களை வரவேற்கிறது.",
    "voice": "Trisha",
    "model": "timbre-v2.5",
    "language": "ta-IN"
  }
  ```
- **Response Format**: Binary audio bytes (`Content-Type: audio/wav`).

---

## 3. Capability Catalogue & Voice Validation
Supported languages and voices are governed by `backend/app/config/capabilities.json` and validated by `CapabilityCatalog`:
- **Tamil (`ta-IN`)**: Voices `Trisha` (female), `Gautam` (male).
- **Indian English (`en-IN`)**: Voices `Kaveri` (female), `Madhav` (male).

The catalogue prevents calling unsupported voice/language combinations, failing fast with informative validation errors.

---

## 4. Error Handling
- **Network / Timeout Failures**: Retried with bounded exponential backoff.
- **Audio Format Mismatch**: The browser normalizes captured audio to 16kHz mono WAV before upload.
- **Provider Outage / Missing Key**: In real mode the application fails fast when `GNANI_API_KEY` is missing. Provider errors are surfaced to the caller and recorded in audit logs.
- **No Silent Fallback**: The backend does not switch to mock, local, or best-effort speech behavior after a provider failure. Mock output is returned only when `PROVIDER_MODE=mock` was explicitly selected.
- **Response Validation**: The STT response must contain a usable transcript. The TTS response must contain audio bytes; blank synthesis text is rejected before the provider call.
- **Submission Limits**: The capability contract exposes a 30-second STT limit, supported audio formats, and the 15 MiB upload limit.
- **Playback Fallback**: If browser autoplay is blocked, the UI exposes a play control and a text fallback. This is a client playback concern, not a provider fallback.

