# KuralCredit Platform Architecture

## 1. Architectural Mission & Overview

KuralCredit is a production-minded, configurable voice workflow platform designed to support multi-domain conversational intake, structured fact extraction, deterministic rule reconciliation, and evidence preparation for human review.

The platform was originally developed for MSME loan clarification in multilingual Indian contexts (Tamil, Tanglish, Hindi, English). Through this transformation, the core conversation and workflow engines have been completely decoupled from loan-specific domain logic into a **generic, data-driven voice workflow engine**. The MSME loan-application workflow is preserved as the first reference implementation (`loan_application`), while a second distinct domain workflow (`customer_support_intake`) runs identically through the same unified engine.

```
+-----------------------------------------------------------------------------+
|                          Presentation Layer (React)                         |
|  - Workflow Discovery & Selection (Consent / Profile)                       |
|  - Multilingual Voice Recorder & Playback (Gnani Prisma / Timbre)           |
|  - Live Transcript Editor & Clarification UI                                |
|  - Synthetic Document Ingestion & Verification                              |
|  - Human Reviewer Evidence Workspace & Audit Timeline                       |
+-----------------------------------------------------------------------------+
                                      |
                                      v REST API (FastAPI)
+-----------------------------------------------------------------------------+
|                            Application / API Layer                          |
|  - Session / Auth & Role Management (Applicant, Reviewer)                   |
|  - Workflow Discovery: GET /api/v1/workflows, GET /workflows/{id}           |
|  - Turn Orchestration: POST /api/v1/applications/{id}/conversation/turns    |
|  - Speech Transcribe / Synthesize: POST /speech/transcribe, /synthesize     |
|  - Document Extraction: POST /api/v1/applications/{id}/documents/upload     |
|  - Fact Corrections: POST /api/v1/facts/{id}/corrections                    |
|  - Review Submission: POST /api/v1/applications/{id}/submit                 |
|  - Reviewer Decisions: POST /api/v1/reviewer/applications/{id}/actions      |
|  - Provider Health & Capability Reporting: /health, /capabilities           |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                        Generic Workflow Engine Core                         |
|  - WorkflowRegistry: In-memory & file-based discovery & validation          |
|  - WorkflowDefinition: Schema, Stages, Transitions, Questions, Doc Profiles |
|  - Stage Transition Manager: Dynamic status advancement & completion logic  |
|  - Field Resolvers: Dynamic metadata, types, constraints, unit parsers      |
|  - Clarification Generator: Targeted questions based on unconfirmed facts   |
+-----------------------------------------------------------------------------+
          |                                                   |
          v                                                   v
+-----------------------------+             +---------------------------------+
|        Provider Layer       |             |       Domain Plugin Layer       |
| - STT Interface             |             | - WorkflowRulePlugin Interface  |
|   * Gnani Prisma STT (Real) |             | - FinancialReconciliationPlugin |
|   * FakeSpeechProvider(Mock)|             | - SupportTriagePlugin           |
| - TTS Interface             |             | - Custom Extractor & Validators |
|   * Gnani Timbre TTS (Real) |             +---------------------------------+
|   * FakeSpeechProvider(Mock)|                               |
| - Reasoning Interface       |                               v
|   * Groq GPT-OSS 120B (Real)|             +---------------------------------+
|   * FakeReasoningProvider   |             |       Persistence & Audit       |
| - Fail-Closed Provider Mode |             | - SQLite / PostgreSQL (SQLModel)|
| - Observable Provider Health|             | - Immutable Audit Event Stream  |
+-----------------------------+             | - Local Document Store          |
                                            +---------------------------------+
```

---

## 2. Layer Responsibilities & Design Principles

### A. Presentation Layer (React + TypeScript)
- **Role**: Discovers active workflows from backend capabilities; renders dynamic form fields, questions, and evidence panels.
- **Independence**: Components contain zero hardcoded MSME loan assumptions. Status labels, stage badges, and field schemas render dynamically based on workflow metadata.
- **Observability**: Explicitly surfaces provider runtime status (`real` vs `mock`), STT latency, Groq token latency, and strict human review disclaimers.

### B. Application & API Layer (FastAPI)
- **Role**: Secure ingress, session creation bound to specific `(workflow_id, workflow_version)` tuples, turn processing, and document ingestion.
- **Fail-Closed Security**: In `real` provider mode, if external credentials or networks fail, API requests fail cleanly with structured error codes (`provider_failure`, `provider_timeout`) rather than silently faking responses.

### C. Generic Workflow Engine Core (`backend/app/domain/workflow`)
- **`WorkflowRegistry`**: Central registry maintaining versioned workflow definitions. All workflows are validated at startup or registration time against `WorkflowDefinition` Pydantic schemas.
- **`WorkflowDefinition`**:
  - `id` & `version`: Unique slug and semantic version (e.g., `loan_application` v1.0.0, `customer_support_intake` v1.0.0).
  - `stages`: Sequence of conversation/processing stages (e.g., `collecting_business_context`, `collecting_financial_context`, `collecting_documents`, `resolving_clarifications`).
  - `fields`: Schema of required and optional facts, data types (`currency`, `scale_unit`, `categorical`, `string`), and extraction hints.
  - `questions`: Stage-linked question templates with localization mappings.
  - `document_profiles`: Document types accepted, extraction rules, and required/optional status.
  - `rule_plugins`: Names of rule plugins executed during reconciliation.
- **Decoupled Orchestration**: Generic `ConversationService` and `ApplicationService` query `registry.get(workflow_id)` to resolve required fields, questions for the active stage, and completion status.

### D. Provider Layer (`backend/app/providers`)
- **Uniform Protocol Adapters**:
  - `SpeechToTextProvider`: Transcribes audio buffers to UTF-8 text with confidence scores and detected languages.
  - `TextToSpeechProvider`: Synthesizes spoken audio from text with configurable voices and rates.
  - `ReasoningProvider`: Executes structured fact extraction and clarification generation with strict JSON schema validation.
- **Explicit Provider Modes**: Controlled via `PROVIDER_MODE=mock|real`. In `mock` mode, local deterministic fakes operate offline for instant, reliable CI tests. In `real` mode, production adapters communicate with Gnani and Groq endpoints with bounded timeouts and zero silent fallbacks.

### E. Domain Plugin Layer (`backend/app/domain/workflow/plugins`)
- **`WorkflowRulePlugin` Protocol**: Defines `evaluate(application, facts, documents, context) -> PluginEvaluationResult`.
- **`FinancialReconciliationPlugin`**: Encapsulates deterministic business rules for loan applications:
  - Compares declared annual turnover vs bank statement total deposits.
  - Checks GST registered sales consistency.
  - Generates neutral clarification items when discrepancies exceed tolerance thresholds.
- **`SupportTriagePlugin`**: Encapsulates deterministic triage rules for customer support tickets:
  - Validates urgency level, error codes, and issue summaries.
  - Recommends SLA routing priority (Tier-1, Tier-2, or Critical Escalation).

---

## 3. Data Flow & Turn Lifecycle

```
[User Utterance (Audio / Text)]
             |
             v
[STT Provider (Gnani Prisma / Fake)] ---> Utterance Transcript
             |
             v
[Reasoning Provider (Groq / Fake)]   ---> Structured Fact Candidates
             |
             v
[Workflow Field Resolvers]          ---> Type Normalization (INR / Scale / Text)
             |
             v
[Workflow Engine Stage Evaluator]   ---> Determines Next Question & Stage Advancement
             |
             v
[Workflow Rule Plugins]             ---> Runs Deterministic Plugins (Reconciliation/Triage)
             |
             v
[TTS Provider (Gnani Timbre / Fake)] ---> Audio Output Stream
             |
             v
[Response Packet to Client]         ---> Updated Conversation, Facts, & Audio
```

---

## 4. Architectural Invariants

1. **Strict Non-Autonomous Boundary**: The platform NEVER makes autonomous lending decisions, credit approvals, risk gradings, or complaint rejections. The system compiles structured, evidence-backed packets for authorized human reviewers.
2. **Deterministic Rules vs. Probabilistic Extraction**: Groq LLM reasoning extracts candidate facts from free-form natural language; deterministic Python plugins evaluate business rules, mathematical differences, and tolerances. The LLM is never permitted to calculate reconciliation discrepancies.
3. **Fail-Closed Provider Integrity**: No fake data in real mode. When real providers are enabled, genuine authenticated network calls are executed.
4. **Source Release Purity**: Zero credentials, virtual environments, node modules, SQLite databases, or audio recordings in release archives.

