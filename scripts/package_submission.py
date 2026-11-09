#!/usr/bin/env python3
"""Build a clean, source-only KuralCredit release ZIP.

The packager uses an allowlist. Local secrets, virtual environments, dependency
trees, databases, uploads, caches and generated build output are never copied.
The completed staging tree is scanned for secrets and forbidden files before the
ZIP is written. The command fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_secrets import scan_path  # noqa: E402

ROOT_FILES = {
    ".env.example",
    ".gitignore",
    "LICENSE",
    "Makefile",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "package.json",
    "package-lock.json",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "uv.lock",
}

INCLUDE_DIRS = (
    "backend/app",
    "backend/tests",
    "docs",
    "scripts",
    "datasets",
    ".github/workflows",
)

INCLUDE_FILES = {
    "backend/Dockerfile",
    "backend/alembic.ini",
    "backend/pyproject.toml",
    "frontend/Dockerfile",
    "frontend/eslint.config.js",
    "frontend/index.html",
    "frontend/nginx.conf",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
}

INCLUDE_PREFIXES = ("frontend/src/",)

EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "release",
    "uploads",
    "smoke_uploads",
    ".git",
    ".benchmarks",
    ".vscode",
    ".idea",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".aac",
    ".m4a",
    ".zip",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

FORBIDDEN_ARCHIVE_PARTS = {
    ".env",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".git",
    "uploads",
    "smoke_uploads",
}


def _excluded(relative: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return True
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if relative.name.startswith(".env") and relative.name != ".env.example":
        return True
    if relative.name in {"Thumbs.db", ".DS_Store"}:
        return True
    return False


def _allowed(relative: Path) -> bool:
    posix = relative.as_posix()
    if posix in ROOT_FILES or posix in INCLUDE_FILES:
        return True
    if any(posix.startswith(prefix) for prefix in INCLUDE_PREFIXES):
        return True
    return any(
        posix == directory or posix.startswith(directory + "/") for directory in INCLUDE_DIRS
    )


def collect_files() -> list[Path]:
    collected: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT)
        if _excluded(relative):
            continue
        if not _allowed(relative):
            continue
        collected.append(path)
    return sorted(set(collected))


def build_archive(output: Path, staging: Path) -> tuple[int, int]:
    files = collect_files()
    if not files:
        raise RuntimeError("Release allowlist produced zero files")

    for source in files:
        relative = source.relative_to(REPO_ROOT)
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    findings = scan_path(staging, release_mode=True)
    if findings:
        details = "\n".join(f"  - {path}: {rule}" for path, rule in sorted(set(findings)))
        raise RuntimeError(f"Release staging failed the secret scan:\n{details}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in files:
            relative = source.relative_to(REPO_ROOT)
            archive.write(source, relative.as_posix())

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    forbidden = [
        name
        for name in names
        if any(part in FORBIDDEN_ARCHIVE_PARTS for part in Path(name).parts)
        or Path(name).name.startswith(".env")
        and Path(name).name != ".env.example"
    ]
    if forbidden:
        raise RuntimeError(f"Archive contains forbidden entries: {forbidden[:10]}")
    if not any(name == "README.md" for name in names):
        raise RuntimeError("Archive is missing README.md")

    return len(files), output.stat().st_size


def write_manifest(output: Path, staging: Path) -> None:
    manifest_txt = output.parent / "RELEASE_FILE_MANIFEST.txt"
    with zipfile.ZipFile(output) as archive:
        names = sorted(archive.namelist())
    manifest_txt.write_text(
        "\n".join(names) + f"\n\nTotal files: {len(names)}\n",
        encoding="utf-8",
    )

    sha256_manifest = output.parent / "MANIFEST.sha256"
    lines: list[str] = []
    for name in names:
        file_path = staging / name
        if file_path.is_file():
            digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {name}")
    # Also record hash of the release archive itself
    archive_digest = hashlib.sha256(output.read_bytes()).hexdigest()
    lines.append(f"{archive_digest}  {output.name}")

    sha256_manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build clean KuralCredit source release")
    parser.parse_args()
    output = REPO_ROOT / "release" / "KuralCredit_Source_Release.zip"

    print("KuralCredit source release packager")
    print(f"  Repository : {REPO_ROOT}")
    print(f"  Output     : {output}")

    with tempfile.TemporaryDirectory(prefix="kuralcredit-release-") as temp:
        staging = Path(temp) / "staging"
        staging.mkdir(parents=True)
        try:
            count, size = build_archive(output, staging)
            write_manifest(output, staging)
        except Exception as exc:
            print(f"[FAIL] {exc}")
            return 1

    print(f"[PASS] Release ZIP created: {output}")
    print(f"       Files: {count}")
    print(f"       Size : {size / 1024:.1f} KiB")
    print(f"       Manifest: {output.parent / 'RELEASE_FILE_MANIFEST.txt'}")
    print(f"       SHA-256 : {output.parent / 'MANIFEST.sha256'}")
    print("       Scan: passed (no .env, secrets, databases, uploads, caches or dependencies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
