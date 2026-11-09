from __future__ import annotations

import re

AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")
ACCOUNT_PATTERN = re.compile(r"(?i)\b(?:a/c|acc(?:ount)?|acct)[^\d]{0,12}(\d{9,18})\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
API_KEY_PATTERN = re.compile(r"\b(?:gsk_|sk-|gai_)[A-Za-z0-9_-]{12,}\b")

REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (API_KEY_PATTERN, "[REDACTED_API_KEY]"),
    (AADHAAR_PATTERN, "[REDACTED_AADHAAR]"),
    (PAN_PATTERN, "[REDACTED_PAN]"),
    (PHONE_PATTERN, "[REDACTED_PHONE]"),
    (EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    (ACCOUNT_PATTERN, "account [REDACTED_ACCOUNT]"),
)


def redact_text(value: str) -> str:
    if not value:
        return value
    redacted = value
    for pattern, replacement in REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_value(value: object) -> object:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value
