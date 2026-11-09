# KuralCredit - Hackathon Submission Checklist & Overview

## Project Details

- **Project Name**: KuralCredit
- **Tagline**: *"Speak naturally. Clarify confidently. Submit an evidence-backed application."*
- **Target Category**: Multilingual Speech-AI / FinTech for Bharat
- **Core Technologies**:
  - **Speech Recognition**: Gnani Prisma STT (`POST /stt/v3`)
  - **Speech Synthesis**: Gnani Timbre TTS (`POST /api/v1/tts/inference`)
  - **Language Reasoning**: Groq `openai/gpt-oss-120b` with strict Pydantic JSON schema output
  - **Full-Stack Toolchain**: FastAPI, React 19, TypeScript, SQLite / PostgreSQL, Python Decimal, ReportLab, OpenPyXL

## Submission Status

Offline rules, contracts, tests, and the production build pass. Live Gnani
Prisma/Timbre and Groq calls are **BLOCKED** until the previously exposed
credentials are rotated. No live provider result is claimed in this
submission. Use explicit `PROVIDER_MODE=mock` for an offline demo; the API
and UI label mock data and mock audio.

## Submission Checklist

| Item | Verification | Status |
|---|---|---|
| **Gnani Prisma STT** | Real adapter, 16kHz WAV normalization, 30s/15MiB validation, mocked contract tests | **IMPLEMENTED; LIVE BLOCKED** |
| **Gnani Timbre TTS** | Real adapter, WAV synthesis, capability validation, playback/error UI, mocked tests | **IMPLEMENTED; LIVE BLOCKED** |
| **Groq GPT-OSS 120B** | Strict schema extraction, bounded retries, no silent fallback, failure-path tests | **IMPLEMENTED; LIVE BLOCKED** |
| **Zero Client Secrets** | Provider keys backend-only; secret scan covers frontend bundle | **PASS (SCANNED)** |
| **Deterministic Rules** | Decimal arithmetic, Indian numbering scales, period and reconciliation rules | **PASS (135/135)** |
| **Document Ingestion** | CSV, XLSX, and PDF parsers with SHA-256 evidence hashes | **PASS (TESTS)** |
| **Responsible AI** | Non-lender boundaries; no autonomous credit or fraud decisions | **PASS (TESTS)** |
| **Complete UI** | React pages, modular CSS, focus states, recorder limit, audio playback | **BUILT** |
| **Automated Tests** | 49 backend tests and 18 frontend tests passing; lint/typecheck/build pass | **PASS (OFFLINE)** |
| **Live Providers** | Adapters wired, opt-in smoke runner available | **BLOCKED** |

## Evidence

- `docs/AI_EVALUATION.md`: 135/135 deterministic cases; explicit mock
  fact extraction; live-provider evaluation marked BLOCKED.
- `docs/READINESS_REPORT.md`: exact commands, security actions, test
  counts, and remaining limitations.
- `scripts/run_provider_smoke_tests.py`: opt-in PASS/FAIL/BLOCKED runner.
  It makes no external calls unless `--live` is supplied.
- `scripts/verify_submission.py`: fail-closed readiness check covering
  fixtures, docs, lint, tests, evaluation, frontend build, and secrets.

## Required Actions Before Live Demo

1. Rotate the Gnani, Groq, application secret, and reviewer credentials
   that were exposed in the local `.env`.
2. Set `PROVIDER_MODE=real` plus the rotated keys in a private `.env`.
3. Run `scripts/run_provider_smoke_tests.py --live` and retain the output.
4. Do not distribute any earlier archive that contained `.env`.

## Key Interview Talking Points

1. **Why Monolith Architecture?**
   Keeps the local demo and evaluation fast, zero-dependency, and
   instantly cloneable without requiring Kafka, Redis, or Kubernetes
   overhead.
2. **Why Separate Reasoning from Arithmetic?**
   LLMs are prone to math errors and hallucinated totals. In KuralCredit,
   Groq is used solely for natural language parsing and neutral question
   framing, while Python `Decimal` performs exact financial math.
3. **Why are Bank Credits Not Revenue?**
   In Indian small businesses, owners routinely transfer personal
   savings, receive loan disbursements, or deposit counter cash into
   current accounts. Equating credits with turnover generates false fraud
   signals. KuralCredit asks neutral clarifying questions instead.
4. **How are Prompt Injections Mitigated?**
   Transcripts and documents are encapsulated as untrusted source data
   with system-level instruction boundaries and strict Pydantic output
   validation.
