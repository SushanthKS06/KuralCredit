from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    application_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    document_type: str
    parser_profile: str
    status: str
    parse_notes: str | None
    page_count: int | None
    metadata_json: dict[str, Any]
    created_at: datetime


class DocumentListOut(BaseModel):
    items: list[DocumentOut]


class DocumentUploadOut(BaseModel):
    document: DocumentOut
    facts_created: int
    extraction_notes: list[str]
