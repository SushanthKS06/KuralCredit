API_V1_PREFIX = "/api/v1"
CONSENT_VERSION = "2026-02-consent-v1"
REQUEST_ID_HEADER = "X-Request-ID"
IDEMPOTENCY_HEADER = "Idempotency-Key"
DEFAULT_CURRENCY = "INR"
SUPPORTED_CURRENCIES = frozenset({"INR"})
AUDIO_CONTENT_TYPES = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/aac": ".aac",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
}
DOCUMENT_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/vnd.ms-excel": ".xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}
REQUIRED_FACT_FIELDS = (
    "business_name",
    "business_type",
    "annual_sales",
    "gst_turnover",
    "bank_credits",
)
REQUIRED_DOCUMENT_TYPES = ("bank_statement",)
