from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ClarificationOut(BaseModel):
    id: str
    application_id: str
    field_key: str
    question_text: str
    reason: str
    expected_answer_type: str
    status: str
    priority: int
    source: str
    language: str
    created_at: datetime
    answered_at: datetime | None
    answer_turn_id: str | None
