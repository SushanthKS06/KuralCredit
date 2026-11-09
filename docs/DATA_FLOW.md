# KuralCredit — Data Flow & Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Applicant
    participant UI as Frontend (React)
    participant API as FastAPI Backend
    participant Gnani as Gnani Prisma & Timbre
    participant Groq as Groq GPT-OSS 120B
    participant DB as Database & File Store
    actor Reviewer

    Applicant->>UI: Speaks declaration (e.g. Tamil/Tanglish)
    UI->>UI: Normalize to 16kHz WAV
    UI->>API: POST /api/v1/speech/transcribe
    API->>Gnani: POST /stt/v3 (Multipart Audio)
    Gnani-->>API: Transcript JSON
    API-->>UI: Raw Transcript & Metadata
    UI->>Applicant: Preview & Edit Transcript
    Applicant->>UI: Confirms Transcript
    UI->>API: POST /api/v1/applications/{id}/conversation/turns
    API->>Groq: POST /chat/completions (Extract Candidate Facts)
    Groq-->>API: Candidate Facts (JSON Schema)
    API->>DB: Persist Candidate Facts with Provenance
    Applicant->>UI: Uploads Bank Statement (CSV)
    UI->>API: POST /api/v1/applications/{id}/documents
    API->>DB: Store Document & SHA-256 Hash
    API->>API: Parse Rows & Run Reconciliations (Decimal)
    Note over API: Declared sales ₹18L vs Bank credits ₹34L
    API->>Groq: Generate Neutral Clarification Question
    Groq-->>API: Clarification Question JSON
    API->>Gnani: POST /api/v1/tts/inference (Timbre)
    Gnani-->>API: Spoken Audio Bytes (WAV)
    API-->>UI: Spoken Clarification Question
    Applicant->>UI: Explains ₹4L personal transfer & cash sales
    UI->>API: POST /api/v1/applications/{id}/conversation/turns
    API->>DB: Attach Explanation to Discrepancy
    Applicant->>UI: Confirms all facts & Submits
    UI->>API: POST /api/v1/applications/{id}/submit
    API->>DB: Transition status: submitted_for_human_review
    Reviewer->>API: GET /api/v1/reviewer/applications/{id}
    API-->>Reviewer: Application Packet + Evidence + Audit Trail
    Reviewer->>API: POST /api/v1/reviewer/applications/{id}/actions (Verify / Close)
```

---

## Data Provenance States

Every financial data point maintains an explicit lifecycle:

| Provenance State | Meaning | Source |
|---|---|---|
| `candidate` | Extracted by AI from speech or unstructured notes; not yet confirmed. | Groq extraction from speech |
| `applicant_confirmed` | Applicant has reviewed, corrected (if needed), and confirmed the figure. | Applicant confirmation |
| `document_extracted` | Extracted deterministically or via AI from an uploaded document. | CSV / XLSX / PDF parser |
| `reviewer_verified` | A human underwriter has reviewed evidence and verified the figure. | Reviewer action |
| `rejected` | Explicitly marked invalid or rejected with recorded justification. | Reviewer / Applicant action |

