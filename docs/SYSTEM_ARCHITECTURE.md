# KuralCredit — System Architecture

```mermaid
flowchart TD
    subgraph Client [Frontend SPA - React 19 / Vite]
        UI[User Interface & Forms]
        Rec[Recorder - MediaRecorder & WAV Normalizer]
        Aud[Audio Player]
        Rev[Reviewer Workspace]
    end

    subgraph Backend [FastAPI Application Server]
        API[API Router /api/v1]
        Auth[Demo Security & Session Manager]
        State[Conversation State Machine]
        Recon[Deterministic Financial Rules - Decimal]
        Parsers[Document Parsers - CSV / XLSX / PDF]
        Audit[Append-Only Audit Log]
    end

    subgraph Providers [Third-Party AI & Speech Providers]
        GnaniSTT[Gnani Prisma STT - api.vachana.ai]
        GnaniTTS[Gnani Timbre TTS - api.vachana.ai]
        GroqLLM[Groq GPT-OSS 120B - api.groq.com]
    end

    subgraph Storage [Persistence Layer]
        DB[(SQLite / PostgreSQL Engine)]
        Disk[Local Encrypted Uploads Storage]
    end

    UI -->|REST + Bearer Token| API
    Rec -->|16kHz Audio WAV| API
    API -->|Synthesized WAV| Aud
    API --> Auth
    API --> State
    API --> Recon
    API --> Parsers
    API --> Audit

    API -->|POST /stt/v3| GnaniSTT
    API -->|POST /api/v1/tts/inference| GnaniTTS
    API -->|POST /chat/completions (JSON Schema)| GroqLLM

    API --> DB
    Parsers --> Disk
```

---

## 1. Architectural Layers & Separation of Concerns

### A. Presentation Layer (Frontend)
- **Framework**: React 19 with TypeScript and Vite.
- **Styling**: Modular CSS (`.module.css`) and shared design tokens (`tokens.css`). Zero Tailwind dependency.
- **Audio Pipeline**:
  - `useRecorder`: Interacts with `navigator.mediaDevices.getUserMedia`.
  - `wav.ts`: Decodes browser audio buffers and resamples to 16kHz 16-bit mono PCM WAV in pure browser TypeScript.
  - `AudioPlayer`: Accessible audio playback for Gnani Timbre responses.
- **State Management**: Local React state paired with typed client wrappers in `api/client.ts`.

### B. Application & API Layer (Backend)
- **Framework**: Python 3.12+ with FastAPI.
- **Validation**: Pydantic v2 schemas for all request/response boundaries.
- **Middleware**:
  - Structured request logging with PII redaction and request correlation IDs (`X-Client-Request-ID`).
  - Strict CORS headers and security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
  - Rate limiting on audio and upload routes.

### C. Domain Logic Layer (Deterministic Engine)
- **Pure Arithmetic**: Python `Decimal` is enforced across all financial amounts. Floats are prohibited in monetary calculations.
- **Number Normalization**: Handles Indian numbering scales (`1,00,000`, `18 lakh`, `1.5 crore`, `Rs. 50,000`).
- **Period Matching**: Standardizes dates to Indian Financial Years (`FY2025-26`: April 1 to March 31) and calendar quarters.
- **Reconciliation Engine**:
  - Rule-based comparison between compatible periods and measures.
  - Distinguishes revenue from bank deposits.
  - Explains variances neutrally without fraud labels.

### D. Provider Adapter Layer
- **Interfaces**: Abstract base classes `SpeechToTextProvider`, `TextToSpeechProvider`, and `ReasoningProvider`.
- **Implementations**:
  - `GnaniSTTProvider`: Real adapter for Prisma STT.
  - `GnaniTTSProvider`: Real adapter for Timbre TTS.
  - `GroqReasoningProvider`: Real adapter for Groq `openai/gpt-oss-120b`.
- **Registry**: Constructed centrally via `ProviderRegistry`; the runtime always uses the real adapters. Tests inject local test doubles through dependency overrides.

---

## 2. Trust Boundaries & Security Enclaves
1. **Frontend / Browser**: Untrusted environment. Provider API keys (`GNANI_API_KEY`, `GROQ_API_KEY`) NEVER touch the frontend bundle or client storage.
2. **Backend API Gateway**: Enforces bearer token authentication, request ID tracing, upload size limits, and rate limits.
3. **LLM Boundary**: Uploaded documents and speech transcripts are treated as untrusted data. Prompts encapsulate inputs under `untrusted_source_data` to mitigate prompt injection.
4. **Human Review Boundary**: The system outputs proposals for human review. No model output can automatically approve, decline, or disburse loans.

