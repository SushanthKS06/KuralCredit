from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    enforce_public_rate_limit,
    get_current_session,
    get_db_dep,
    get_settings_dep,
)
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError, ValidationAppError
from app.models.base import utcnow
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import SessionCreateRequest, SessionInfo, SessionOut
from app.schemas.common import MessageResponse
from app.services.session_service import SessionContext, SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
def create_session(
    payload: SessionCreateRequest,
    request: Request,
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
) -> SessionOut:
    enforce_public_rate_limit("sessions", request, settings)
    if payload.role == "applicant":
        raise ValidationAppError(
            "Applicant sessions are created automatically with POST /applications"
        )
    if not payload.email or not payload.password:
        raise ValidationAppError("Reviewer login requires email and password")
    issued = SessionService(db, settings).issue_reviewer_session(payload.email, payload.password)
    db.commit()
    return SessionOut(
        token=issued.token,
        session_id=issued.session_id,
        role="reviewer",
        application_id=None,
        display_name=issued.display_name,
        expires_at=issued.expires_at,
    )


@router.get("/me", response_model=SessionInfo)
def session_info(
    session: SessionContext = Depends(get_current_session),
) -> SessionInfo:
    return SessionInfo(
        session_id=session.session_id,
        role=session.role,
        application_id=session.application_id,
        display_name=session.display_name,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    session: SessionContext = Depends(get_current_session),
    db: Session = Depends(get_db_dep),
) -> MessageResponse:
    record = SessionRepository(db).get(session.session_id)
    if record is None:
        raise UnauthorizedError("Session is not active")
    record.revoked_at = utcnow()
    db.commit()
    return MessageResponse(message="Signed out.")
