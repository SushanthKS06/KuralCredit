#!/usr/bin/env python3
"""Redacted secret and release-hygiene scanner for KuralCredit.

The scanner never prints matched secret values. It reports only the file,
rule name and a redacted placeholder so findings can be fixed safely.

Usage:
    python scripts/check_secrets.py
    python scripts/check_secrets.py --release --path release/staging
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".benchmarks",
    "dist",
    "release",
    "uploads",
    "smoke_uploads",
}
SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".aac",
    ".m4a",
    ".pdf",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".zip",
}
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".css",
    ".html",
    ".example",
    "",
}

# Filenames that must never appear in a source release.
FORBIDDEN_RELEASE_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
}

SENSITIVE_KEY_NAMES = (
    "GNANI_API_KEY",
    "GROQ_API_KEY",
    "SECRET_KEY",
    "REVIEWER_DEMO_PASSWORD",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
)

PLACEHOLDER_PREFIXES = (
    "",
    "replace",
    "your",
    "changeme",
    "placeholder",
    "example",
    "test-",
    "test_",
    "fake-",
    "fake_",
    "demo-",
    "demo_",
    "ci-",
    "<",
    "${",
)

ENV_ASSIGNMENT = re.compile(r"(?im)^\s*(?P<key>[A-Z][A-Z0-9_]{2,})\s*=\s*(?P<value>[^\r\n#]+)")
TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("groq_style_api_key", re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b")),
    ("openai_style_api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{24,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)


def _is_placeholder(value: str) -> bool:
    cleaned = value.strip().strip("'\"")
    lowered = cleaned.lower()
    if not lowered:
        return True
    return lowered.startswith(PLACEHOLDER_PREFIXES)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name.lower() not in SKIP_DIRS]
        for name in names:
            path = Path(current) / name
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix:
                continue
            files.append(path)
    return files


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def load_local_secret_values() -> list[str]:
    """Load secret values from a local .env for value-leak scanning.

    The values are returned only for in-memory comparison. They are never
    printed or written anywhere.
    """
    env_path = REPO_ROOT / ".env"
    values: list[str] = []
    if not env_path.exists():
        return values
    text = _read_text(env_path) or ""
    for match in ENV_ASSIGNMENT.finditer(text):
        key = match.group("key")
        value = match.group("value").strip().strip("'\"")
        if key in SENSITIVE_KEY_NAMES and not _is_placeholder(value) and len(value) >= 8:
            values.append(value)
    return values


def scan_path(root: Path, *, release_mode: bool = False) -> list[tuple[str, str]]:
    """Return (relative path, rule) findings without exposing secret values."""
    root = root.resolve()
    findings: list[tuple[str, str]] = []
    secret_values = load_local_secret_values()

    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        name = path.name.lower()
        if name.startswith(".env") and name != ".env.example" and not release_mode:
            # A local .env is intentionally outside the source scan. The
            # packager rejects it by filename and the release-mode scan below
            # fails closed if it ever reaches a staging tree.
            continue
        if release_mode:
            if name in FORBIDDEN_RELEASE_NAMES and name != ".env.example":
                findings.append((relative, "forbidden_release_file"))
                continue
            if name.endswith((".pem", ".key", ".p12", ".pfx")):
                findings.append((relative, "forbidden_private_key_file"))
                continue

        text = _read_text(path)
        if text is None:
            continue

        for key_name in SENSITIVE_KEY_NAMES:
            for match in re.finditer(
                rf"(?im)^\s*{re.escape(key_name)}\s*=\s*(?P<value>[^\r\n#]+)", text
            ):
                if not _is_placeholder(match.group("value")):
                    findings.append((relative, f"populated_secret_assignment:{key_name}"))

        for rule, pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                findings.append((relative, rule))

        if secret_values:
            for value in secret_values:
                if value in text:
                    findings.append((relative, "local_env_secret_value_embedded"))
                    break

        if "GNANI_API_KEY" in text and relative.startswith("frontend/src"):
            findings.append((relative, "provider_secret_name_in_frontend_source"))

    return findings


def scan_frontend_bundle(root: Path = REPO_ROOT) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    dist_dir = root / "frontend" / "dist"
    if not dist_dir.exists():
        return findings
    secret_values = load_local_secret_values()
    for path in dist_dir.rglob("*"):
        if not path.is_file():
            continue
        text = _read_text(path)
        if text is None:
            continue
        relative = path.relative_to(root).as_posix()
        for name in ("GNANI_API_KEY", "GROQ_API_KEY", "X-API-Key-ID"):
            if name in text:
                findings.append((relative, f"backend_secret_name_in_bundle:{name}"))
        for value in secret_values:
            if value in text:
                findings.append((relative, "local_env_secret_value_in_bundle"))
                break
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Redacted KuralCredit secret scan")
    parser.add_argument("--path", default=str(REPO_ROOT), help="Directory or file to scan")
    parser.add_argument(
        "--release",
        action="store_true",
        help="Also fail on forbidden release filenames (.env, keys, databases are skipped by suffix)",
    )
    parser.add_argument(
        "--include-frontend-bundle",
        action="store_true",
        help="Scan frontend/dist for leaked provider secret names or values",
    )
    args = parser.parse_args()

    root = Path(args.path)
    findings = scan_path(root, release_mode=args.release)
    if args.include_frontend_bundle and root.resolve() == REPO_ROOT:
        findings.extend(scan_frontend_bundle(REPO_ROOT))

    if findings:
        print("[FAIL] Secret/release scan found issues (values are redacted):")
        for relative, rule in sorted(set(findings)):
            print(f"  - {relative}: {rule}")
        print(f"  Total findings: {len(set(findings))}")
        return 1

    print(
        "[PASS] No hardcoded provider secrets, embedded local values, or forbidden release files found."
    )
    local_env = REPO_ROOT / ".env"
    if local_env.exists():
        print("  Note: a local .env exists and is intentionally excluded from scans and releases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
