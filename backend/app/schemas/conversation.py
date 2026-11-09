from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.clarification import ClarificationOut


class TurnCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    input_mode: Literal["text", "audio"] = "text"
    language: str | None = Field(default=None, max_length=20)
    stt_request_id: str | None = Field(default=None, max_length=120)
    stt_latency_ms: float | None = Field(default=None, ge=0)
    stt_model: str | None = Field(default=None, max_length=60)
    confirmed_transcript: bool = False
    clarification_id: str | None = None

    @model_validator(mode="after")
    def require_audio_confirmation(self) -> TurnCreate:
        if self.input_mode == "audio" and not self.confirmed_transcript:
            raise ValueError("Audio transcripts must be confirmed or corrected before submission")
        return self


class TurnOut(BaseModel):
    id: str
    application_id: str
    turn_index: int
    speaker: str
    input_mode: str
    transcript: str
    language: str
    intent: str | None
    target_field: str | None
    question_id: str | None
    linked_fact_ids: list[str]
    provider_metadata: dict[str, Any]
    correction_status: str
    created_at: datetime


class NextQuestionOut(BaseModel):
    question_id: str
    field_key: str
    prompt: str
    reason: str
    expected_answer_type: str
    source: Literal["workflow", "clarification"]
    clarification_id: str | None = None


class ConversationOut(BaseModel):
    application_id: str
    status: str
    stage: str
    turns: list[TurnOut]
    next_question: NextQuestionOut | None
    open_clarifications: list[ClarificationOut]
    candidate_facts_count: int
    note: str | None = None


class TurnResponse(BaseModel):
    turn: TurnOut
    facts_created: int
    candidate_field_keys: list[str]
    extraction_notes: list[str] = Field(default_factory=list)
    next_question: NextQuestionOut | None
    conversation: ConversationOut
