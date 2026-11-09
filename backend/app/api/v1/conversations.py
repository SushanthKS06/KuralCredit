from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    enforce_rate_limit,
    get_conversation_service,
    get_owned_application,
    get_readable_application,
    get_settings_dep,
    require_applicant,
)
from app.core.config import Settings
from app.models.application import Application
from app.schemas.conversation import ConversationOut, TurnCreate, TurnResponse
from app.services.conversation_service import ConversationService
from app.services.session_service import SessionContext

router = APIRouter(tags=["conversation"])


@router.get("/applications/{application_id}/conversation", response_model=ConversationOut)
def get_conversation(
    application: Application = Depends(get_readable_application),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationOut:
    return service.get_conversation(application)


@router.post("/applications/{application_id}/conversation/turns", response_model=TurnResponse)
def submit_turn(
    payload: TurnCreate,
    application: Application = Depends(get_owned_application),
    session: SessionContext = Depends(require_applicant),
    settings: Settings = Depends(get_settings_dep),
    service: ConversationService = Depends(get_conversation_service),
) -> TurnResponse:
    enforce_rate_limit("conversation_turn", session, settings)
    return service.submit_turn(application, payload, actor=f"applicant:{application.id}")
