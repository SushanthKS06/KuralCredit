from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    get_application_service,
    get_db_dep,
    get_idempotency_key,
    get_reconciliation_service,
    get_review_service,
    get_reviewer_application,
    load_idempotent_response,
    require_reviewer,
    store_idempotent_response,
)
from app.core.exceptions import ValidationAppError
from app.core.lifecycle import ApplicationStatus
from app.models.application import Application
from app.schemas.review import (
    ReviewActionOut,
    ReviewActionRequest,
    ReviewerApplicationOut,
    ReviewQueueOut,
)
from app.services.application_service import ApplicationService
from app.services.export_service import ExportService
from app.services.reconciliation_service import ReconciliationService
from app.services.review_service import ReviewService
from app.services.session_service import SessionContext

router = APIRouter(prefix="/reviewer", tags=["reviewer"])


@router.get("/queue", response_model=ReviewQueueOut)
def review_queue(
    query: str | None = Query(default=None, max_length=120),
    status: str | None = Query(
        default=None,
        description="Comma-separated application statuses; defaults to the active review queue.",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: SessionContext = Depends(require_reviewer),
    service: ReviewService = Depends(get_review_service),
) -> ReviewQueueOut:
    statuses = None
    if status:
        requested = {item.strip() for item in status.split(",") if item.strip()}
        valid = {item.value for item in ApplicationStatus}
        unknown = requested - valid
        if unknown:
            raise ValidationAppError(f"Unknown review statuses: {sorted(unknown)}")
        statuses = requested
    return service.queue(query=query, limit=limit, offset=offset, statuses=statuses)


@router.get("/applications/{application_id}", response_model=ReviewerApplicationOut)
def reviewer_application(
    application: Application = Depends(get_reviewer_application),
    service: ReviewService = Depends(get_review_service),
) -> ReviewerApplicationOut:
    return service.detail(application)


@router.post("/applications/{application_id}/actions", response_model=ReviewActionOut)
def review_action(
    payload: ReviewActionRequest,
    response: Response,
    application: Application = Depends(get_reviewer_application),
    session: SessionContext = Depends(require_reviewer),
    service: ReviewService = Depends(get_review_service),
    db: Session = Depends(get_db_dep),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> ReviewActionOut:
    scope = f"review:{application.id}:{payload.action}"
    stored = load_idempotent_response(db, scope, idempotency_key)
    if stored is not None:
        response.headers["Idempotent-Replay"] = "true"
        return stored
    action = service.act(application, payload, reviewer_name=session.display_name)
    store_idempotent_response(db, scope, idempotency_key, action.model_dump(mode="json"))
    return action


@router.get("/applications/{application_id}/export")
def reviewer_export(
    application: Application = Depends(get_reviewer_application),
    db: Session = Depends(get_db_dep),
    application_service: ApplicationService = Depends(get_application_service),
    reconciliation: ReconciliationService = Depends(get_reconciliation_service),
) -> JSONResponse:
    packet = ExportService(db, application_service, reconciliation).reviewer_packet(application)
    return JSONResponse(
        content=packet,
        headers={
            "Content-Disposition": (
                f'attachment; filename="kuralcredit-{application.reference}-review.json"'
            ),
            "Cache-Control": "no-store",
        },
    )
