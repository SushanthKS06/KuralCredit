#!/usr/bin/env python3
"""Fail-closed submission readiness verification for KuralCredit.

Checks are intentionally evidence-based: a missing frontend bundle, failed
test suite, failed evaluation, or secret scan finding makes this script exit
non-zero. It uses the active Python interpreter instead of assuming a local
virtual-environment path.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
DOCS_DIR = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

REQUIRED_DOCS = [
    "README.md",
    "docs/BASELINE_AUDIT.md",
    "docs/ARCHITECTURE.md",
    "docs/WORKFLOW_AUTHORING.md",
    "docs/PROVIDER_VERIFICATION.md",
    "docs/TESTING.md",
    "docs/PRODUCT_REQUIREMENTS.md",
    "docs/SYSTEM_ARCHITECTURE.md",
    "docs/DATA_FLOW.md",
    "docs/API_CONTRACTS.md",
    "docs/SECURITY_AND_PRIVACY.md",
    "docs/AI_EVALUATION.md",
    "docs/GNANI_INTEGRATION.md",
    "docs/GROQ_INTEGRATION.md",
    "docs/DEMO_SCRIPT.md",
    "docs/HACKATHON_SUBMISSION.md",
    "docs/READINESS_REPORT.md",
    "docs/ADR/0001-monolith-first.md",
    "docs/ADR/0002-provider-adapters.md",
    "docs/ADR/0003-human-review-boundary.md",
]

REQUIRED_FIXTURES = [
    "backend/app/fixtures/synthetic_applicants.json",
    "backend/app/fixtures/synthetic_applications.json",
    "backend/app/fixtures/evaluation_utterances.jsonl",
    "backend/app/fixtures/mock_transcripts.json",
    "backend/app/fixtures/synthetic_financial_records/sample_bank_statement.csv",
    "backend/app/fixtures/synthetic_financial_records/sample_gst_summary.csv",
    "backend/app/config/capabilities.json",
]


def _run(
    args: list[str],
    *,
    cwd: Path,
    label: str,
    shell: bool = False,
) -> bool:
    print(f"\n[CHECK] {label}")
    print(f"  $ {' '.join(args)}")
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=shell,
        )
    except OSError as exc:
        print(f"  [FAIL] Could not start command: {exc}")
        return False
    if result.returncode == 0:
        print("  [PASS]")
        return True
    print(f"  [FAIL] Exit code {result.returncode}")
    output = (result.stdout or "") + (result.stderr or "")
    if output.strip():
        lines = output.strip().splitlines()
        for line in lines[-25:]:
            print(f"    {line}")
    return False


def _npm_command() -> list[str] | None:
    npm = shutil.which("npm")
    if not npm:
        print("  [FAIL] npm is not available on PATH")
        return None
    if sys.platform == "win32":
        return ["cmd.exe", "/c", npm]
    return [npm]


def check_fixtures() -> bool:
    print("\n[CHECK] Synthetic fixtures")
    all_ok = True
    for relative in REQUIRED_FIXTURES:
        path = REPO_ROOT / relative
        if not path.exists() or path.stat().st_size == 0:
            print(f"  [FAIL] Missing or empty fixture: {relative}")
            all_ok = False
        else:
            print(f"  [PASS] {relative} ({path.stat().st_size} bytes)")
    return all_ok


def check_docs() -> bool:
    print("\n[CHECK] Required documentation")
    all_ok = True
    for relative in REQUIRED_DOCS:
        path = REPO_ROOT / relative
        if not path.exists() or path.stat().st_size < 50:
            print(f"  [FAIL] Missing or incomplete doc: {relative}")
            all_ok = False
        else:
            print(f"  [PASS] {relative} ({path.stat().st_size} bytes)")
    return all_ok


def check_backend_lint() -> bool:
    return _run(
        [sys.executable, "-m", "ruff", "check", "backend", "scripts"],
        cwd=REPO_ROOT,
        label="Backend and script lint",
    )


def check_backend_tests() -> bool:
    return _run(
        [sys.executable, "-m", "pytest", "backend/tests", "-q"],
        cwd=REPO_ROOT,
        label="Backend test suite",
    )


def check_evaluation() -> bool:
    return _run(
        [sys.executable, "scripts/run_evaluation.py"],
        cwd=REPO_ROOT,
        label="Deterministic evaluation benchmark",
    )


def check_frontend() -> bool:
    npm = _npm_command()
    if npm is None:
        return False
    if not (FRONTEND_DIR / "node_modules").exists():
        print("\n[CHECK] Frontend dependencies")
        print("  [FAIL] frontend/node_modules is missing; run npm install first")
        return False
    lint_ok = _run(
        npm + ["run", "lint"],
        cwd=FRONTEND_DIR,
        label="Frontend lint",
    )
    tests_ok = _run(
        npm + ["run", "test", "--", "--run"],
        cwd=FRONTEND_DIR,
        label="Frontend unit tests",
    )
    build_ok = _run(
        npm + ["run", "build"],
        cwd=FRONTEND_DIR,
        label="Frontend production build",
    )
    if not lint_ok or not tests_ok or not build_ok:
        return False
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    assets = list((FRONTEND_DIR / "dist" / "assets").glob("*.js"))
    print("\n[CHECK] Frontend build artifacts")
    if not dist_index.exists() or dist_index.stat().st_size < 100:
        print("  [FAIL] frontend/dist/index.html is missing or too small")
        return False
    if not assets:
        print("  [FAIL] frontend/dist/assets contains no JavaScript bundle")
        return False
    print(f"  [PASS] index.html plus {len(assets)} JavaScript bundle(s)")
    return True


def check_secrets() -> bool:
    return _run(
        [
            sys.executable,
            "scripts/check_secrets.py",
            "--include-frontend-bundle",
        ],
        cwd=REPO_ROOT,
        label="Secret and release-hygiene scan",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify KuralCredit submission readiness.")
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip frontend tests/build (backend CI job; frontend job covers it).",
    )
    args = parser.parse_args()

    print("=" * 68)
    print("  KuralCredit Submission Readiness Verification")
    print("=" * 68)
    print(f"  Python: {sys.executable}")
    print(f"  Repo:   {REPO_ROOT}")

    results = [
        ("fixtures", check_fixtures()),
        ("docs", check_docs()),
        ("lint", check_backend_lint()),
        ("backend tests", check_backend_tests()),
        ("evaluation", check_evaluation()),
    ]

    if args.skip_frontend:
        print("\n[CHECK] Frontend tests/build")
        print("  [SKIPPED] --skip-frontend was supplied; the frontend CI job covers it.")
    else:
        results.append(("frontend", check_frontend()))

    results.append(("secrets", check_secrets()))

    print("\n" + "=" * 68)
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL':<5} {name}")
    if failed:
        print(f"  [INCOMPLETE] Failed checks: {', '.join(failed)}")
        return 1
    print("  [READY] All selected submission readiness checks passed.")
    print(
        "  Live Gnani/Groq calls are not part of this check; "
        "use scripts/run_provider_smoke_tests.py --live after credential rotation."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
