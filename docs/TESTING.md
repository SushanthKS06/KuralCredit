# Testing & Verification Guide

This guide details all testing tiers across the KuralCredit codebase, covering unit tests, integration tests, contract tests, deterministic evaluation benchmarks, and live provider smoke tests.

---

## 1. Test Architecture & Tiers

The test suite is organized into 5 distinct tiers to maintain deterministic, fast, offline-first development:

```
+-----------------------------------------------------------------------+
| 1. Unit Tests (backend/tests/unit)                                    |
|    - Workflow engine validation & registry checks                     |
|    - Money parsing, Indian numbering scales (Lakh/Crore), dates       |
|    - Reconciliation tolerances & domain rule plugins                  |
|    - Provenance tracking & audit log event integrity                  |
|    - Configuration safety & fail-closed error handling                 |
+-----------------------------------------------------------------------+
| 2. Contract Tests (backend/tests/contract)                            |
|    - REST API request/response schemas                                |
|    - Provider request & JSON response schemas                         |
+-----------------------------------------------------------------------+
| 3. Integration Tests (backend/tests/integration)                      |
|    - Multi-workflow end-to-end lifecycle (loan & customer support)    |
|    - Voice turn conversation flow with fact extraction                |
|    - Synthetic document upload and reconciliation                     |
|    - Human reviewer queue, evidence inspection, and audit trail       |
+-----------------------------------------------------------------------+
| 4. Deterministic Evaluation Suite (scripts/run_evaluation.py)         |
|    - 135 evaluation vectors across 5 benchmarks                       |
|    - Money extraction, scale normalization, period resolution         |
|    - Discrepancy detection & clarification generation                 |
+-----------------------------------------------------------------------+
| 5. Live Provider Smoke Tests (scripts/run_provider_smoke_tests.py)    |
|    - Authenticated tests against real Gnani STT, Gnani TTS, and Groq  |
|    - Opt-in via --live flag; requires real credentials                |
+-----------------------------------------------------------------------+
```

---

## 2. Test Execution Commands

### A. Backend Test Suite (Pytest)
Runs all 56 backend tests offline:
```powershell
python -m pytest backend/tests -v
```
*Note on Windows Sandbox*: On Windows inside sandboxed process isolation, Python's `anyio` loopback socketpair requires standard socket permissions. When running pytest with FastAPI `TestClient`, use standard terminal execution.

### B. Deterministic Evaluation Benchmark
Runs all 135 deterministic evaluation vectors across 5 test suites:
```powershell
python scripts/run_evaluation.py
```
Expected output:
- `extraction_accuracy`: 100.0% (30/30)
- `scale_normalization`: 100.0% (25/25)
- `period_resolution`: 100.0% (20/20)
- `discrepancy_detection`: 100.0% (30/30)
- `clarification_relevance`: 100.0% (30/30)
- Overall status: `PASS (100.0% accuracy across 135 vectors)`

### C. Multi-Workflow Integration Tests
Validates discovery and execution of both `loan_application` and `customer_support_intake`:
```powershell
python -m pytest backend/tests/integration/test_multi_workflow_execution.py -v
```

### D. Frontend Unit Tests (Vitest)
Executes all 18 frontend component and integration tests:
```powershell
cd frontend
npm test -- --run
```

### E. Frontend Lint & Build
```powershell
cd frontend
npm run lint
npm run build
```

### F. Secret & Hygiene Scan
Verifies that no secrets, `.env` files, or binary artifacts are present in tracked files or staging:
```powershell
python scripts/check_secrets.py
```

### G. Live Provider Smoke Tests (Opt-In)
Executes authenticated requests to Gnani and Groq endpoints:
```powershell
python scripts/run_provider_smoke_tests.py --live
```

### H. Complete Submission Readiness Verification
Executes full submission verification pipeline fail-closed:
```powershell
python scripts/verify_submission.py
```

