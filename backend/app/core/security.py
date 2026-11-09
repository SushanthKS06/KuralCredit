from __future__ import annotations

import hashlib
import hmac
import re
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock

import jwt

from app.core.exceptions import RateLimitedError, UnauthorizedError, ValidationAppError

SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def create_session_token(
    *,
    session_id: str,
    role: str,
    application_id: str | None,
    secret_key: str,
    ttl_hours: int,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": session_id,
        "role": role,
        "app_id": application_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
        "iss": "kuralcredit",
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_session_token(token: str, secret_key: str) -> dict[str, object]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"], issuer="kuralcredit")
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Session has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid session token") from exc
    return payload


def verify_demo_password(submitted: str, expected: str) -> bool:
    return hmac.compare_digest(submitted.encode("utf-8"), expected.encode("utf-8"))


def sanitize_filename(filename: str) -> str:
    base = Path(filename).name
    cleaned = SAFE_FILENAME_PATTERN.sub("_", base).strip("._")
    if not cleaned:
        raise ValidationAppError("Filename is invalid")
    if len(cleaned) > 120:
        stem = Path(cleaned).stem[:80]
        suffix = Path(cleaned).suffix[:10]
        cleaned = f"{stem}{suffix}"
    return cleaned


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ensure_within_directory(base: Path, candidate: Path) -> Path:
    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if base_resolved != candidate_resolved and base_resolved not in candidate_resolved.parents:
        raise ValidationAppError("Resolved path escapes the storage directory")
    return candidate_resolved


def file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self.window_seconds = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise RateLimitedError("Too many requests. Please wait before retrying.")
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
