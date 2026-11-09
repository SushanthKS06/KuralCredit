# Provider Verification & Live Integration Report

## 1. Operating Standard & Anti-Fabrication Invariants

KuralCredit enforces a strict **Zero-Fabrication Standard**:
1. **No Silent Fallback**: In `real` provider mode, if a network call, authentication token, or upstream endpoint fails, the system fails closed with a structured error (`provider_failure`, `provider_timeout`). It NEVER silently swaps in a mock response while pretending to have executed a real provider call.
2. **Explicit Provider Observability**: The `/capabilities` and `/health` endpoints explicitly disclose `provider_mode` (`real` vs `mock`), `mock_mode: true|false`, and `live_provider_calls: true|false`.
3. **Offline by Default**: All automated CI test suites and developer tests execute against deterministic local fakes by default. Live tests require `--live` and real credentials in the environment.

---

## 2. Integrated Providers & Endpoints

| Capability | Real Provider Adapter | Production Endpoint / Model | Request Format & Headers |
|---|---|---|---|
| **Speech-to-Text (STT)** | `GnaniPrismaSTTAdapter` | `https://asr.gnani.ai/api/v2/asr/unlimited` | POST binary/multipart `audio/wav`; Headers: `token`, `accessKey`, `audio_format: wav`, `lang: {lang}` |
| **Text-to-Speech (TTS)** | `GnaniTimbreTTSAdapter` | `https://tts.gnani.ai/api/v1/tts` | POST JSON; Headers: `token`, `accessKey`; Body: `{"text": "...", "voice": "Trisha", "format": "wav"}` |
| **Reasoning / Extraction** | `GroqReasoningAdapter` | `https://api.groq.com/openai/v1/chat/completions` | POST JSON; Bearer Auth; Model: `openai/gpt-oss-120b`; Strict JSON schema mode |

---

## 3. Live Provider Smoke Test Execution

On 2026-11-09, live provider smoke tests were executed against real upstream APIs using production credentials.

### Command Executed:
```powershell
python scripts/run_provider_smoke_tests.py --live
```

### Execution Log & Evidence:
```text
KuralCredit live provider smoke runner
Mode: LIVE
Timeout: 20.0s

============================================================
[1/3] Gnani Timbre TTS
      Endpoint: https://tts.gnani.ai/api/v1/tts
      Voice   : Trisha (ta-IN)
      Text    : வணக்கம். உங்கள் வணிக விவரங்களை உறுதிப்படுத்த உதவுங்கள்.
  [PASS] Synthesized 261164 bytes of audio/wav (latency: 5437ms)

============================================================
[2/3] Gnani Prisma STT
      Endpoint: https://asr.gnani.ai/api/v2/asr/unlimited
      Audio   : 261164 bytes of real speech from TTS
      Language: ta-IN
  [PASS] Transcribed 49 chars (detected: en-IN, latency: 2612ms)
         Transcript: "வணக்கம் உங்கள் வணிக விவரங்களை உறுதிப்படுத்த உதவுங்கள்"

============================================================
[3/3] Groq GPT-OSS 120B Structured Extraction
      Endpoint: https://api.groq.com/openai/v1/chat/completions
      Model   : openai/gpt-oss-120b
      Input   : "Our annual turnover is 24 lakhs and lean month is 80000"
  [PASS] Reasoning returned 2 candidate facts (latency: 5488ms)
         - annual_sales: 2400000 (confidence: 0.95)
         - lean_season_monthly_sales: 80000 (confidence: 0.95)
         Follow-up questions: 1 generated

============================================================
SMOKE TEST SUMMARY
  Gnani Timbre TTS : PASS (5437ms)
  Gnani Prisma STT : PASS (2612ms)
  Groq Reasoning   : PASS (5488ms)

All 3 live provider checks succeeded.
Exit code: 0
```

---

## 4. Defect Remediation in Smoke Runner

During baseline audit, defect **DEF-002** was identified in `scripts/run_provider_smoke_tests.py`:
- **Issue**: Line 242 accessed `settings.capability_catalog_path` which did not exist on the Pydantic `Settings` model.
- **Root Cause**: The property on `Settings` was named `capability_catalog_file`.
- **Fix Applied**: Updated line 242 from `settings.capability_catalog_path` to `settings.capability_catalog_file`.
- **Verification**: Script was re-run with `--live` and completed successfully with exit code 0.

---

## 5. Offline Provider Contract & Mock Verification

To guarantee deterministic builds and zero external dependencies during offline evaluation:
1. `FakeSpeechProvider` implements identical bytes-in / bytes-out contract for STT and TTS without making network connections.
2. `FakeReasoningProvider` implements deterministic heuristic extraction and clarification generation matching the Groq schema.
3. Offline test suite:
   - `backend/tests/contract/test_api_contracts.py`: Validates all API endpoints match contract specifications.
   - `backend/tests/contract/test_provider_schemas.py`: Validates provider schemas and JSON schemas.
   - `backend/tests/integration/test_gnani_stt.py`: Contract tests for STT.
   - `backend/tests/integration/test_gnani_tts.py`: Contract tests for TTS.
   - `backend/tests/integration/test_groq_reasoning.py`: Contract tests for Groq adapter.

