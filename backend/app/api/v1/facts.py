from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db_dep,
    get_readable_application,
    require_applicant,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.application import Application
from app.repositories.fact_repository import FactRepository
from app.schemas.financial_fact import (
    FactCorrectionRequest,
    FactCorrectionResponse,
    FinancialFactListOut,
)
from app.services.evidence_service import EvidenceService
from app.services.serializers import fact_out
from app.services.session_service import SessionContext

router = APIRouter(tags=["facts"])


@router.get("/applications/{application_id}/facts", response_model=FinancialFactListOut)
def list_facts(
    application: Application = Depends(get_readable_application),
    db: Session = Depends(get_db_dep),
) -> FinancialFactListOut:
    facts = FactRepository(db).list_for_application(application.id)
    return FinancialFactListOut(items=[fact_out(fact) for fact in facts])


@router.post("/facts/{fact_id}/corrections", response_model=FactCorrectionResponse)
def correct_fact(
    fact_id: str,
    payload: FactCorrectionRequest,
    session: SessionContext = Depends(require_applicant),
    db: Session = Depends(get_db_dep),
) -> FactCorrectionResponse:
    fact = FactRepository(db).get(fact_id)
    if fact is None:
        raise NotFoundError("Financial fact not found")
    if session.application_id != fact.application_id:
        raise ForbiddenError("You can only change facts from your own application")
    service = EvidenceService(db)
    actor = f"applicant:{fact.application_id}"
    if payload.action == "confirm":
        return service.confirm(fact, actor)
    if payload.action == "correct":
        return service.correct(fact, payload, actor)
    assert payload.reason is not None
    return service.reject(fact, payload.reason, actor)
