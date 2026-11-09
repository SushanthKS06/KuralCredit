from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_readable_application, get_reconciliation_service
from app.models.application import Application
from app.schemas.reconciliation import ReconciliationOut
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(tags=["reconciliation"])


@router.get(
    "/applications/{application_id}/reconciliation",
    response_model=ReconciliationOut,
)
def get_reconciliation(
    application: Application = Depends(get_readable_application),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationOut:
    return service.out(application)
