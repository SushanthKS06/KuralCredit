# KuralCredit Baseline Audit & Defect Register

**Date:** 2026-11-09  
**Auditor:** Principal Software Architect & QA Lead  
**Repository Root:** `E:\KuralCredit`  
**OS / Python / Node Environment:** Windows 11 / Python 3.14.3 / Node.js 20+ (npm 10.8.2)

---

## 1. Executive Summary

A comprehensive baseline audit of the KuralCredit repository was conducted prior to making any architectural modifications. The audit identified:
- **1 P0 Critical Security Defect**: Active API keys for Gnani and Groq were found in the local root `.env` file. Since no `.git` directory is present in the workspace, Git commit history inspection was not possible. Immediate credential rotation is required for any keys that were distributed.
- **1 P1 High-Priority Runtime Defect**: `scripts/run_provider_smoke_tests.py` crashed when invoked with `--live` due to an invalid attribute reference (`settings.capability_catalog_path` instead of `settings.capability_catalog_file`).
- **1 P1 Architectural Defect**: Domain coupling to MSME loan fields throughout generic services (`ConversationService`, `ApplicationService`, `fact_definitions.py`, `conversation_state.py`), preventing multi-domain workflow reuse.
- **Several P2/P3 Enhancement & Packaging Defects**: Missing SHA-256 manifest in release generation, lack of workflow discovery APIs, absence of a second non-loan demonstration workflow, and loan-specific UI assumptions.

All existing baseline offline tests (49 backend pytest cases, 18 frontend Vitest cases, Ruff lint, ESLint, TypeScript compilation, and production build) currently pass.

---

## 2. Baseline Test & Check Execution Log

| Check | Exact Command | Exit Code | Result / Output Summary |
|---|---|:---:|---|
| **Git Status Check** | `git status` | 1 | `fatal: not a git repository (or any of the parent directories): .git`. Historical commit inspection not possible. |
| **Local Secret Scan** | `python scripts/check_secrets.py` | 0 | `[PASS]` (local `.env` excluded by default scanner design; staging/release scanner fails closed if included). |
| **Ruff Lint Check** | `python -m ruff check backend scripts` | 0 | `All checks passed!` |
| **Backend Test Suite** | `python -m pytest backend/tests -v` | 0 | `49 passed, 2 warnings in 12.82s`. |
| **Frontend TypeScript** | `cd frontend && npx tsc --noEmit` | 0 | 0 errors. |
| **Frontend Unit Tests** | `cd frontend && npm test -- --run` | 0 | `6 passed (6 files), 18 passed (18 tests) in 6.30s`. |
| **Frontend ESLint** | `cd frontend && npm run lint` | 0 | 0 errors. |
| **Frontend Production Build** | `cd frontend && npm run build` | 0 | `dist/index.html` (0.64 kB), `dist/assets/index-Dt6Pc8M3.css` (45.20 kB), `dist/assets/index-FZ3-KnmE.js` (368.60 kB). |
| **Evaluation Benchmark** | `python scripts/run_evaluation.py` | 0 | 100% pass across all 5 deterministic benchmarks (135 total test vectors). |
| **Submission Verification** | `python scripts/verify_submission.py` | 0 | All 7 check stages passed. |
| **Offline Provider Smoke** | `python scripts/run_provider_smoke_tests.py` | 1 | `[BLOCKED] --live was not supplied`. Offline fail-closed guard operates correctly. |
| **Live Smoke Test (Initial)** | `python scripts/run_provider_smoke_tests.py --live --provider groq` | 1 | `AttributeError: 'Settings' object has no attribute 'capability_catalog_path'`. (DEF-002). |
| **Live Smoke Test (Post-Fix)** | `python scripts/run_provider_smoke_tests.py --live` | 0 | **STT: PASS** (49 chars, en-IN, 2612 ms), **TTS: PASS** (261,164 bytes, 5437 ms), **Groq: PASS** (2 candidate facts, openai/gpt-oss-120b, 5488 ms). |
| **Release Packager** | `python scripts/package_submission.py` | 0 | Created `release/KuralCredit_Source_Release.zip` (308 files, 392.1 KiB). Manifest lacks SHA-256 hashes. |

---

## 3. Defect Register

### DEF-001: Root `.env` Populated with Real Provider Secrets
- **Severity**: P0 (Security & Release Hygiene)
- **Component**: Root configuration / Repository hygiene
- **Reproduction**: Inspect `E:\KuralCredit\.env`. Lines 9 and 23 contain active provider credentials for Gnani and Groq.
- **Root Cause**: Developer environment secrets were left in the project root directory.
- **Fix**:
  1. The `.gitignore` ignores `.env` and `.env.*`.
  2. `check_secrets.py` and `package_submission.py` ensure `.env` is never staged or bundled in any release archive.
  3. Safe `.env.example` contains placeholders only (`GNANI_API_KEY=`, `GROQ_API_KEY=`).
  4. Explicit developer advisory issued to rotate both keys if they were ever checked into external repositories or shared archives.
- **Test Proving Fix**: `python scripts/check_secrets.py --release --path release/staging` and `python scripts/package_submission.py` fail closed if any `.env` or secret appears in staging.
- **Status**: Remediated in packager; credential rotation advisory documented.

---

### DEF-002: Live Provider Smoke Tests Crash on Missing Settings Attribute
- **Severity**: P1 (Functional / Verification Tooling)
- **Component**: `scripts/run_provider_smoke_tests.py`
- **Reproduction**: Run `python scripts/run_provider_smoke_tests.py --live`.
- **Root Cause**: Line 242 accessed `settings.capability_catalog_path` which does not exist on `Settings` (the field is `gnani_capability_catalog_path` and the resolved property is `capability_catalog_file`).
- **Fix**: Updated line 242 to `CapabilityCatalog.load(settings.capability_catalog_file)`.
- **Test Proving Fix**: `python scripts/run_provider_smoke_tests.py --live` runs to completion and exits 0 with all three providers verified live.
- **Status**: FIXED & VERIFIED.

---

### DEF-003: Hardcoded MSME Loan Coupling in Generic Conversation & Application Services
- **Severity**: P1 (Architecture / Platform Generality)
- **Component**: `backend/app/services/conversation_service.py`, `backend/app/services/application_service.py`, `backend/app/domain/fact_definitions.py`, `backend/app/domain/conversation_state.py`
- **Reproduction**: Attempt to register or execute a second non-loan workflow (e.g., customer support intake). The conversation service crashes or enforces `business_type`, `annual_sales`, `gst_turnover`, and bank statement document checks.
- **Root Cause**: MSME loan domain fields and rules were hardcoded directly in the orchestration services rather than declared in modular workflow definition schemas.
- **Fix**:
  1. Implement a declarative `WorkflowDefinition` schema and `WorkflowRegistry`.
  2. Move loan-specific fields, question templates, completion criteria, and document requirements into a modular `loan_application` workflow definition.
  3. Isolate loan reconciliation rules into a domain plugin (`loan_plugin`).
  4. Refactor `ConversationService` and `ApplicationService` to operate entirely on the session's active workflow schema.
  5. Implement a second genuinely working workflow (`customer_support_intake`).
- **Test Proving Fix**: Create unit and integration tests executing both `loan_application` and `customer_support_intake` through the exact same engine.
- **Status**: In Progress (Stage 3).

---

### DEF-004: Release Packager Lacks Cryptographic File Manifest (SHA-256)
- **Severity**: P2 (Packaging / Verifiable Delivery)
- **Component**: `scripts/package_submission.py`
- **Reproduction**: Inspect `release/RELEASE_FILE_MANIFEST.txt`. It only contains filenames without file integrity hashes.
- **Root Cause**: `write_manifest()` in `scripts/package_submission.py` wrote file paths without computing SHA-256 digests.
- **Fix**: Update `scripts/package_submission.py` to calculate SHA-256 hashes for all archived members and write `release/MANIFEST.sha256`.
- **Test Proving Fix**: Re-run packager and verify `release/MANIFEST.sha256` formatting and file integrity check.
- **Status**: Scheduled (Stage 7).

---

### DEF-005: Missing Workflow Discovery and Detail APIs
- **Severity**: P2 (API / Integration)
- **Component**: `backend/app/api/v1/`
- **Reproduction**: Query `/api/v1/workflows`. Returns 404.
- **Root Cause**: Endpoints for discovering available workflows and querying active workflow schemas were not implemented.
- **Fix**: Add `GET /api/v1/workflows` and `GET /api/v1/workflows/{workflow_id}` endpoints returning workflow metadata, supported input modes, languages, and field definitions.
- **Test Proving Fix**: Contract and integration tests validating workflow discovery.
- **Status**: Scheduled (Stage 3).

---

### DEF-006: Frontend Application Creation Lacks Workflow Selection
- **Severity**: P2 (Frontend UX / Dynamic Platform)
- **Component**: `frontend/src/pages/ConsentPage.tsx`, `frontend/src/pages/LandingPage.tsx`
- **Reproduction**: Open application creation flow. Only loan application is supported with fixed business name / applicant name fields.
- **Root Cause**: UI forms hardcoded loan application creation instead of dynamically reading available workflows from `/api/v1/workflows`.
- **Fix**: Add workflow selection step or dropdown populated from `/api/v1/workflows`, allowing the user to initiate either the MSME loan clarification workflow or the customer support intake workflow.
- **Test Proving Fix**: Frontend unit tests verifying workflow selector rendering and submission.
- **Status**: Scheduled (Stage 6).

---

## 4. Environment and Runtime Invariants

1. **Python Version**: Python 3.14.3 on Windows 11.
2. **Network / Socket Invariant in Windows Sandbox**: In standard sandbox mode on Windows, localhost loopback socket connections require elevated permissions or explicit bypass to prevent `socket.socketpair` from blocking during asyncio/anyio event loop creation.
3. **Provider Invariant**:
   - `PROVIDER_MODE=real`: Requires valid `GNANI_API_KEY` and `GROQ_API_KEY`. Never silently falls back to mocks.
   - `PROVIDER_MODE=mock`: Explicitly designated for offline demo/test runs. Visibly labelled as mock mode. Production startup fails closed if mock mode is configured.

