from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: str
    application_id: str | None
    actor: str
    event_type: str
    summary: str
    detail_json: dict[str, Any]
    created_at: datetime


class AuditListOut(BaseModel):
    items: list[AuditEventOut]
