from __future__ import annotations

from app.core.lifecycle import ApplicationStatus
from app.domain.conversation_state import (
    WORKFLOW_QUESTIONS,
    ConversationStage,
    questions_for_stage,
    stage_for_status,
)


def test_conversation_stages_and_questions():
    stage = stage_for_status(ApplicationStatus.COLLECTING_BUSINESS_CONTEXT)
    assert stage == ConversationStage.BUSINESS_CONTEXT

    questions = questions_for_stage(stage)
    assert len(questions) >= 1
    assert questions[0].stage == ConversationStage.BUSINESS_CONTEXT
    assert any(q.field_key == "business_type" for q in WORKFLOW_QUESTIONS)
