# KuralCredit — Groq GPT-OSS 120B Integration Guide

## 1. Overview
KuralCredit uses Groq's high-speed inference engine with model **`openai/gpt-oss-120b`** for:
1. **Applicant Fact Extraction**: Extracting candidate business turnover, sales, and GST figures from natural spoken transcripts.
2. **Document Summary & Extraction**: Interpreting unstructured lines, invoices, and table extracts.
3. **Neutral Clarification Generation**: Generating single, focused, context-aware follow-up questions when financial declarations and bank credits diverge.
4. **Reviewer Executive Summaries**: Summarizing verified evidence and noting limitations for human credit underwriters.

Groq is strictly segregated from arithmetic and financial decisions. All mathematical operations and reconciliation tolerances are handled deterministically in Python.

### Provider mode and live status

- `PROVIDER_MODE=real`: uses the configured Groq adapter with strict
  structured output and bounded retries.
- `PROVIDER_MODE=mock`: uses the explicit `LocalTestReasoningAdapter` for
  deterministic tests and offline demos. Its output is labelled as mock
  and is not a measurement of live model quality.
- Live Groq verification is **BLOCKED** until the exposed credentials are
  rotated. The contract below is a configuration reference, not evidence
  that a live request succeeded.

---

## 2. API Contract & Configuration
- **Base URL**: `https://api.groq.com/openai/v1`
- **Path**: `POST /chat/completions`
- **Authentication**: `Authorization: Bearer <GROQ_API_KEY>`
- **Model**: `openai/gpt-oss-120b` (configurable via `GROQ_MODEL`)
- **Parameters**:
  - `temperature`: `0.1` (low temperature for deterministic fact extraction)
  - `reasoning_effort`: `low` (configurable via `GROQ_REASONING_EFFORT`)
  - `response_format`: `{"type": "json_schema", "json_schema": {"name": ..., "strict": true, "schema": ...}}`

### Failure semantics

- Authentication errors, rate-limit exhaustion, timeouts, HTTP 400
  responses, and invalid structured output surface as errors.
- The adapter retries transient failures with bounded backoff.
- The adapter does not automatically retry a request without strict schema
  constraints, and it does not substitute local or mock extraction after a
  real-provider failure.
- Malformed model output is rejected rather than accepted as best effort.
- Mock reasoning is selected only by explicit provider mode or explicit
  adapter choice in tests.

---

## 3. Structured Outputs & Pydantic Validation
To prevent unpredictable freeform responses, all Groq calls enforce structured outputs validated via Pydantic schemas:

1. **`ApplicantFactExtraction`**:
   - `candidate_facts`: list of extracted fields (`field_key`, `raw_value`, `normalized_candidate`, `currency`, `period_start`, `period_end`, `evidence_quote`, `confidence_estimate`).
   - `missing_fields`: required fields not mentioned.
   - `clarification_candidates`: ambiguous statements requiring follow-up.
2. **`ClarificationGeneration`**:
   - `question`: single neutral question.
   - `reason`: explanation of why the question is asked.
   - `expected_answer_type`: expected format (e.g. `currency`, `text`, `explanation`).
3. **`ReviewerSummaryOutput`**:
   - `applicant_declared_facts`: confirmed statements.
   - `document_derived_facts`: verified document facts.
   - `applicant_explanations`: explanations for variances.
   - `unresolved_items`: items lacking evidence.
   - `limitations`: explicit disclosure of non-comparable measures.

---

## 4. Prompt Versioning & Registry
Prompts are versioned and stored under `backend/app/prompts/`:
- `safety_policy_v1.txt`: Enforces non-lender boundaries, prohibits credit decisions, and prevents fraud accusations.
- `fact_extraction_v1.txt`: Instructs model to extract only grounded facts without guessing.
- `clarification_v1.txt`: Guides model to formulate neutral, non-leading questions.
- `reviewer_summary_v1.txt`: Produces objective evidence digests for underwriters.

The `PromptRegistry` dynamically loads and checks prompt templates at startup.

