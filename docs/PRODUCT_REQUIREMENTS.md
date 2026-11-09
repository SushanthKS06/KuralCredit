# KuralCredit â€” Product Requirements Document (PRD)

**Product Tagline:**
> *"Speak naturally. Clarify confidently. Submit an evidence-backed application."*

---

## 1. Executive Summary & Purpose
KuralCredit is a multilingual, voice-first loan application clarification and evidence preparation system built for micro, small, and medium enterprises (MSMEs) in India. 

Small business owners in India frequently face language barriers, non-standard record-keeping (such as physical cash registers and mixed personal/business bank accounts), and unfamiliarity with English-first digital credit portals. KuralCredit allows applicants to explain their business operations, seasonal sales variations, and banking transactions in their preferred Indian language (e.g. Tamil, Tanglish, or Indian English), transcribing speech via **Gnani Prisma STT**, reasoning over declarations and synthetic documents using **Groq-hosted openai/gpt-oss-120b**, delivering spoken feedback via **Gnani Timbre TTS**, and packaging the results for a human credit officer.

---

## 2. Hard Non-Goals & System Boundaries
To maintain strict compliance and credit integrity, KuralCredit is **explicitly bounded**:

- **NOT a Lender or Underwriting Engine**: KuralCredit never approves, declines, scores, prices, or determines the creditworthiness of an applicant.
- **NOT a Credit Bureau or Fraud Detector**: The system does not report to bureaus or classify applicants as "fraudulent".
- **Does NOT Equate Bank Credits with Revenue**: Bank credits reflect total cash/transfer inflows, which routinely include loans, owner capital infusions, inter-account transfers, and non-business credits.
- **Does NOT Autonomously Invent Financial Values**: Missing information is flagged explicitly as missing, never hallucinated or zero-filled.
- **Does NOT Perform Autonomous Financial Actions**: The application cannot disburse funds or commit loan origination without human oversight.

---

## 3. Primary Personas & User Journeys

### Persona A: Small Business Applicant (e.g., Textile Retailer in Madurai)
- **Problem**: Needs to apply for working capital before festival season. Uncomfortable with complex accounting terms and English web forms. Has â‚¹18L declared sales, â‚¹16.5L GST turnover, and â‚¹34L in bank credits (including a â‚¹4L savings transfer and cash counter receipts).
- **Journey**:
  1. Opens KuralCredit on mobile or desktop; reads privacy and consent notice.
  2. Selects Tamil (`ta-IN`) and preferred voice (`Trisha`).
  3. Speaks answers about business turnover and operations.
  4. Reviews and confirms the speech transcript preview (with inline correction capability).
  5. Groq GPT-OSS 120B extracts candidate facts (annual sales, declared GST turnover).
  6. Uploads synthetic bank statement (CSV/PDF) and sales register.
  7. Deterministic rule engine flags variance between declared sales and bank credits.
  8. Assistant speaks a neutral clarification question: *"Bank credits exceed declared sales. Were there transfers or cash receipts?"*
  9. Applicant explains the â‚¹4L transfer and cash sales; explanation is attached to the record.
  10. Applicant reviews the completeness packet and submits for human review.

### Persona B: Credit Reviewer / Underwriter
- **Problem**: Receives borrower applications with fragmented records and unexplained variances, wasting hours in back-and-forth communication.
- **Journey**:
  1. Authenticates into Reviewer Dashboard.
  2. Views application queue filtered by status, submission date, and completeness score.
  3. Opens application packet; views declared facts side-by-side with document-extracted facts and SHA-256 hashes.
  4. Listens to speech transcript excerpts and reviews applicant's contextual explanations.
  5. Reviews AI-generated summary with clear limitations and caveats.
  6. Takes audited action: *Verify Fact*, *Request More Information*, or *Mark Review Completed*.
  7. Exports sanitized JSON packet for the institutional Loan Origination System (LOS).

---

## 4. Key Functional Requirements

| ID | Requirement | Implementation |
|---|---|---|
| **FR-01** | Multilingual Voice Capture | Browser MediaRecorder with 16kHz mono WAV normalization |
| **FR-02** | Speech-to-Text | Gnani Prisma STT (`POST /stt/v3`) with transcript confirmation |
| **FR-03** | Text-to-Speech | Gnani Timbre TTS (`POST /api/v1/tts/inference`) with WAV synthesis and browser playback |
| **FR-04** | Candidate Fact Extraction | Groq model `openai/gpt-oss-120b` with strict Pydantic JSON schema |
| **FR-05** | Document Ingestion | CSV, XLSX, and searchable PDF parsers with SHA-256 provenance |
| **FR-06** | Deterministic Reconciliation | Python `Decimal` arithmetic; period and measure compatibility checks |
| **FR-07** | Neutral Clarifications | Single-question clarification generator focused on unexplained variances |
| **FR-08** | Reviewer Command Center | Queue management, fact verification, and audit trail |
| **FR-09** | Exportable Evidence Packet | Sanitized JSON packet export with reviewer boundary notices |
| **FR-10** | Safe Fallbacks & Degradation | Text-only interview fallback and explicit provider error reporting |


