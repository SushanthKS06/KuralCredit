# KuralCredit — API Contracts & Endpoints Reference

All endpoints are versioned under `/api/v1` and documentable via Swagger UI at `/docs`.

---

## 1. System & Capabilities

### `GET /api/v1/health`
Returns system liveness, database status, and active provider operational status.
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "ok",
  "providers": {
    "stt_provider": "gnani-prisma",
    "tts_provider": "gnani-timbre",
    "reasoning_provider": "groq",
    "gnani_stt_configured": true,
    "gnani_tts_configured": true,
    "groq_configured": true
  }
}
```

### `GET /api/v1/capabilities`
Returns supported languages, selectable voices, defaults, and feature flags.
```json
{
  "catalog_version": "2026.11",
  "languages": [
    {
      "code": "ta-IN",
      "name": "Tamil",
      "native_name": "தமிழ்",
      "script": "Taml",
      "stt_supported": true,
      "voices": [
        { "name": "Trisha", "gender": "female", "model": "timbre-v2.5" },
        { "name": "Kaveri", "gender": "female", "model": "timbre-v2.5" }
      ]
    }
  ]
}
```

---

## 2. Sessions & Authentication

### `POST /api/v1/sessions`
Creates an authenticated session for an applicant or reviewer.
**Request:**
```json
{
  "role": "reviewer",
  "email": "reviewer@kuralcredit.demo",
  "password": "test-reviewer-password"
}
```
**Response:** `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsIn...",
  "session_id": "sess_091283",
  "role": "reviewer",
  "display_name": "Credit Reviewer",
  "expires_at": "2026-11-08T18:00:00Z"
}
```

---

## 3. Speech Services

### `POST /api/v1/speech/transcribe`
Uploads 16kHz mono WAV audio for transcription via Gnani Prisma STT.
**Form Data:**
- `application_id`: UUID
- `language`: `ta-IN`
- `audio`: audio/wav binary file
**Response:** `200 OK`
```json
{
  "transcript": "எங்க கடை சென்ற வருட விற்பனை பதினெட்டு லட்சம் ரூபாய்.",
  "language": "ta-IN",
  "detected_language": "ta-IN",
  "provider": "gnani-prisma",
  "model": "prisma-v3.0",
  "request_id": "req-99120",
  "latency_ms": 340.5
}
```

### `POST /api/v1/speech/synthesize`
Synthesizes approved text to speech using Gnani Timbre TTS.
**Request:**
```json
{
  "application_id": "app_uuid",
  "text": "வணக்கம், உங்கள் ஆவணங்களை பதிவேற்றவும்.",
  "language": "ta-IN",
  "voice": "Trisha"
}
```
**Response:** `200 OK` with binary audio payload (`Content-Type: audio/wav`).

---

## 4. Applications & Conversation

### `POST /api/v1/applications`
Creates a new application with explicit consent.
**Request:**
```json
{
  "applicant_name": "Meenakshi Sundaram",
  "business_name": "Meenakshi Textiles",
  "language": "ta-IN",
  "voice": "Trisha",
  "consent_accepted": true
}
```

### `POST /api/v1/applications/{id}/conversation/turns`
Submits a confirmed transcript or text response, triggering Groq fact extraction.
**Request:**
```json
{
  "text": "Last year annual sales were 18 lakh and GST turnover was 16.5 lakh.",
  "input_mode": "audio",
  "confirmed_transcript": true
}
```

### `POST /api/v1/applications/{id}/submit`
Submits application packet for human review. Enforces idempotency via `Idempotency-Key` header.
**Request:**
```json
{
  "confirm_accuracy": true,
  "acknowledge_no_decision": true
}
```

---

## 5. Reviewer Operations

### `GET /api/v1/reviewer/queue`
Returns applications pending human review with completeness percentages.

### `POST /api/v1/reviewer/applications/{id}/actions`
Records an audited human review decision.
**Request:**
```json
{
  "action": "verify_fact",
  "field_key": "annual_sales",
  "reason": "Verified against sales register and bank customer receipts."
}
```

### `GET /api/v1/reviewer/applications/{id}/export`
Exports a sanitized application packet (JSON) for the institutional loan system.

