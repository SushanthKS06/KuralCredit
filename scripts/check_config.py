#!/usr/bin/env python3
"""Configuration diagnostic utility for KuralCredit.

Validates environment variables, provider credentials, directories, and database connectivity
without logging or exposing any secret values.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import build_engine  # noqa: E402


def main() -> int:
    print("=" * 60)
    print("  KuralCredit Configuration Diagnostic")
    print("=" * 60)

    try:
        settings = get_settings()
    except Exception as exc:
        print(f"[FAIL] Configuration validation error: {exc}")
        return 1

    diagnostics = settings.redacted_diagnostics()
    for key, value in sorted(diagnostics.items()):
        print(f"  {key:<35}: {value}")

    print("\n--- Diagnostic Checks ---")

    # Check 1: Upload directory
    upload_path = settings.upload_path
    try:
        upload_path.mkdir(parents=True, exist_ok=True)
        test_file = upload_path / ".perm_check"
        test_file.write_text("ok")
        test_file.unlink()
        print(f"  [PASS] Upload directory writable: {upload_path}")
    except Exception as exc:
        print(f"  [FAIL] Upload directory not writable: {exc}")
        return 1

    # Check 2: Database connectivity
    try:
        engine = build_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"  [PASS] Database reachable: {settings.database_url.split('///')[0]}///...")
    except Exception as exc:
        print(f"  [FAIL] Database unreachable: {exc}")
        return 1

    # Check 3: Providers Status
    print(f"  [INFO] Gnani API Key configured: {settings.gnani_configured}")
    print(f"  [INFO] Groq API Key configured: {settings.groq_configured}")

    print("\n[OK] Configuration check completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
