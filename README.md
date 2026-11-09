# KuralCredit

> **"Speak naturally. Clarify confidently. Submit an evidence-backed application."**

[![CI](https://github.com/kuralcredit/kuralcredit/actions/workflows/ci.yml/badge.svg)](https://github.com/kuralcredit/kuralcredit/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/frontend-React%2019-61DAFB.svg)](https://react.dev/)
[![Speech](https://img.shields.io/badge/speech-Gnani%20Prisma%20%2B%20Timbre-orange.svg)](https://vachana.ai/)
[![Reasoning](https://img.shields.io/badge/reasoning-Groq%20GPT--OSS%20120B-f55036.svg)](https://groq.com/)

---

## 1. What is KuralCredit?

**KuralCredit** is a configurable, multilingual voice workflow platform. Originally built to clarify MSME loan applications across Indian languages (Tamil, Tanglish, Hindi, English), the platform now features a **reusable, data-driven voice workflow engine** that orchestrates conversational intake, structured candidate fact extraction, deterministic domain rule evaluation, and evidence preparation for human review.

The platform includes two fully functional, end-to-end workflows:
1. **`loan_application` (Reference Workflow)**: Multilingual MSME loan clarification, turnover declaration, and reconciliation against bank statements and GST records.
2. **`customer_support_intake` (Demonstration Workflow)**: Cross-domain support ticket and triage workflow demonstrating engine reusability without changing conversation or provider code.

Core Platform Capabilities:
1. **Transcribes Spoken Declarations**: Using **Gnani Prisma STT**, applicants and users speak naturally in vernacular languages.
2. **Interactive Transcript Confirmation**: Users inspect and correct transcripts before fact extraction.
3. **Structured Candidate Fact Extraction**: Using **Groq-hosted `openai/gpt-oss-120b`**, candidate fields are parsed into strict Pydantic schemas.
4. **Deterministic Accounting Arithmetic**: Python `Decimal` handles Indian numbering scales (`18 lakh`, `1.5 crore`) and period matching. Floats are prohibited in monetary calculations.
5. **Neutral Variance Clarification**: Differences between declared revenue and bank deposits are flagged neutrally. **Gnani Timbre TTS** speaks follow-up questions to understand cash counter sales or owner transfers.
6. **Evidence-Backed Human Review Packet**: Compiles an auditable evidence packet with cryptographic SHA-256 hashes for human reviewers.

---

## 2. Hard Non-Goals & System Boundaries

### Current verification status

- **Live Provider Integration**: Real authenticated requests were executed and **PASSED** for Gnani Prisma STT, Gnani Timbre TTS, and Groq GPT-OSS 120B reasoning (`python scripts/run_provider_smoke_tests.py --live`).
- **Offline Deterministic Verification**: 56 backend tests, 18 frontend tests, and 135 AI evaluation vectors **100% PASS**.
- **Provider Mode Integrity**: The platform supports both `PROVIDER_MODE=real` (fails closed on upstream errors) and `PROVIDER_MODE=mock` (deterministic local fakes clearly labeled in UI and API). See [`docs/READINESS_REPORT.md`](docs/READINESS_REPORT.md).

KuralCredit is **NOT**:
- A lender, loan originator, credit bureau, or underwriting engine.
- A credit scoring, eligibility, approval, rejection, or risk-pricing system.
- A fraud detector.
- A system that assumes bank credits equal revenue.
- A system that invents missing financial values.
- An autonomous agent allowed to disburse loans or make binding credit decisions.

All final decisions require human review.

---

## 3. Technology Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite / PostgreSQL.
- **Speech AI**: Gnani Prisma STT (`POST /stt/v3`) & Gnani Timbre TTS (`POST /api/v1/tts/inference`).
- **Language Reasoning**: Groq `openai/gpt-oss-120b` with strict Pydantic JSON schema output.
- **Document Ingestion**: Python `csv`, `openpyxl` (XLSX), and `pypdf` / `reportlab` (PDF).
- **Frontend**: React 19, TypeScript, Vite, Modular CSS (`.module.css`). Zero Tailwind dependency.
- **Audio Capture**: Browser `MediaRecorder` with client-side 16kHz mono 16-bit PCM WAV encoding.

---

## 4. Quickstart & Installation

### Prerequisites
- Python 3.11+ or 3.12 (Python 3.12 recommended)
- Node.js 18+ and npm
- `uv` package manager (optional, but recommended)

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/kuralcredit/kuralcredit.git
cd KuralCredit

# Copy example environment configuration
cp .env.example .env

# For an offline demo without provider keys, set:
# PROVIDER_MODE=mock
```

### 2. Install Dependencies
```bash
# Set up Python virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -e "backend[dev]"

# Install frontend dependencies
npm --prefix frontend install
```

### 3. Verify Configuration
Run the automated configuration check to verify upload directories, database, and settings:
```bash
python scripts/check_config.py
```

### 4. Build Synthetic Documents
```bash
# Generate synthetic bank statements, GST summaries, and sales registers
python scripts/create_synthetic_documents.py
```

### 5. Build Frontend
```bash
npm --prefix frontend run build
```

### 6. Run the Application
Start the FastAPI server (it automatically serves the React UI and API endpoints):
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Open your browser at **`http://127.0.0.1:8000`**.

---

## 5. Reviewer Access

- **Applicant Experience**: Open `http://127.0.0.1:8000` and click *"Start New Application"*.
- **Reviewer Portal**: Navigate to `/reviewer/login`.
  - **Email**: `reviewer@kuralcredit.demo`
  - **Password**: `test-reviewer-password`

---

## 6. Provider Verification & Testing

### Running Tests
```bash
.venv\Scripts\python.exe -m pytest backend/tests -q
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

### Running Deterministic Evaluation
```bash
# Offline rules and explicit mock-adapter benchmark; no external calls
.venv\Scripts\python.exe scripts/run_evaluation.py
```

### Running Live Provider Smoke Tests (Opt-In)
The smoke runner makes no external calls by default. After rotating the
exposed credentials and setting `PROVIDER_MODE=real`:
```bash
.venv\Scripts\python.exe scripts/run_provider_smoke_tests.py --live
```
Without `--live`, or in mock mode, it reports `BLOCKED` and exits non-zero
instead of claiming a provider was verified.

### Verify Submission Readiness
```bash
# Full check, including frontend lint/tests/build and the secret scan
.venv\Scripts\python.exe scripts/verify_submission.py

# Backend-only CI mode
.venv\Scripts\python.exe scripts/verify_submission.py --skip-frontend
```

---

## 7. Configuration Reference (`.env`)

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Application environment (`development` / `production`) | `development` |
| `PROVIDER_MODE` | Real provider calls or explicit labelled mock/demo mode | `real` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./kuralcredit.db` |
| `GNANI_API_KEY` | Gnani API key for Prisma STT and Timbre TTS | Backend only |
| `GNANI_API_BASE_URL` | Gnani API gateway host | `https://api.vachana.ai` |
| `GNANI_STT_MODEL` | Prisma STT model identifier | `prisma-v3.0` |
| `GNANI_TTS_MODEL` | Timbre TTS model identifier | `timbre-v2.5` |
| `GROQ_API_KEY` | Groq API Key | Backend only |
| `GROQ_MODEL` | Model ID for language reasoning | `openai/gpt-oss-120b` |
| `LOG_REDACT_PII` | Enables redaction of sensitive identifiers in logs | `true` |
| `AUDIO_RETENTION_ENABLED` | Persist uploaded audio when explicitly enabled | `false` |

Mock mode requires no provider keys and is rejected when `APP_ENV=production`.
Never commit `.env`; rotate any credential that has been exposed.

---

## 8. Documentation Directory

Detailed architectural specifications, evaluation benchmarks, and integration guides are available in `docs/`:
- [`docs/BASELINE_AUDIT.md`](docs/BASELINE_AUDIT.md): Inventory audit, environment constraints, and defect register.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Generic voice workflow platform architecture and layer separation.
- [`docs/WORKFLOW_AUTHORING.md`](docs/WORKFLOW_AUTHORING.md): Step-by-step guide to authoring new schemas, questions, and plugins.
- [`docs/PROVIDER_VERIFICATION.md`](docs/PROVIDER_VERIFICATION.md): Upstream Gnani and Groq live verification evidence and latencies.
- [`docs/TESTING.md`](docs/TESTING.md): Testing tiers, commands, and verification procedures.
- [`docs/PRODUCT_REQUIREMENTS.md`](docs/PRODUCT_REQUIREMENTS.md): User personas, functional requirements, and product boundaries.
- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md): Component diagrams, trust boundaries, and modular separation.
- [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md): Sequence diagram and fact provenance states.
- [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md): Full REST API contract examples.
- [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md): Data minimization, redaction, and prompt injection defense.
- [`docs/AI_EVALUATION.md`](docs/AI_EVALUATION.md): Deterministic benchmark results and live-provider limitations.
- [`docs/READINESS_REPORT.md`](docs/READINESS_REPORT.md): Comprehensive readiness report and defect register.
- [`docs/GNANI_INTEGRATION.md`](docs/GNANI_INTEGRATION.md): Prisma STT and Timbre TTS request/response specifications.
- [`docs/GROQ_INTEGRATION.md`](docs/GROQ_INTEGRATION.md): Groq GPT-OSS 120B structured output configuration.
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md): Step-by-step 3-minute hackathon demo script.
- [`docs/HACKATHON_SUBMISSION.md`](docs/HACKATHON_SUBMISSION.md): Submission checklist and interview talking points.
- [`docs/ADR/`](docs/ADR/): Architecture Decision Records (Monolith first, Provider adapters, Human review boundary).

---

## 9. License
MIT License. See [LICENSE](LICENSE) for details.

