from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import (
    enforce_public_rate_limit,
    get_application_service,
    get_current_session,
    get_db_dep,
    get_idempotency_key,
    get_owned_application,
    get_readable_application,
    get_settings_dep,
    get_storage_dep,
    load_idempotent_response,
    store_idempotent_response,
)
from app.core.config import Settings
from app.models.application import Application
from app.schemas.application import (
    ApplicationCreate,
    ApplicationCreatedOut,
    ApplicationDetailOut,
    ApplicationListOut,
    ApplicationOut,
    ApplicationUpdate,
    ConsentRequest,
    DeleteResponse,
    SubmitRequest,
    SubmitResponse,
    WithdrawRequest,
)
from app.services.application_service import ApplicationService
from app.services.session_service import SessionContext
from app.storage.local_storage import LocalStorage

router = APIRouter(prefix="/applications", tags=["applications"])


def _detail(service: ApplicationService, application: Application) -> ApplicationDetailOut:
    return ApplicationDetailOut(
        application=ApplicationOut.model_validate(application),
        completeness=service.completeness(application),
    )


@router.post("", response_model=ApplicationCreatedOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    request: Request,
    service: ApplicationService = Depends(get_application_service),
    settings: Settings = Depends(get_settings_dep),
) -> ApplicationCreatedOut:
    enforce_public_rate_limit("applications", request, settings)
    application, completeness, issued = service.create_application(payload)
    return ApplicationCreatedOut(
        application=ApplicationOut.model_validate(application),
        completeness=completeness,
        token=issued.token,
        session_id=issued.session_id,
        expires_at=issued.expires_at,
    )


@router.get("", response_model=ApplicationListOut)
def list_applications(
    status: str | None = Query(default=None, max_length=50),
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: SessionContext = Depends(get_current_session),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationListOut:
    application_id = session.application_id if session.role == "applicant" else None
    items, total = service.list_applications(
        status=status,
        query=query,
        limit=limit,
        offset=offset,
        application_id=application_id,
    )
    return ApplicationListOut(
        items=[ApplicationOut.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{application_id}", response_model=ApplicationDetailOut)
def get_application(
    application: Application = Depends(get_readable_application),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationDetailOut:
    return _detail(service, application)


@router.patch("/{application_id}", response_model=ApplicationDetailOut)
def update_application(
    payload: ApplicationUpdate,
    application: Application = Depends(get_owned_application),
    session: SessionContext = Depends(get_current_session),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationDetailOut:
    updated = service.update_application(application, payload, actor=f"applicant:{application.id}")
    return _detail(service, updated)


@router.post("/{application_id}/consent", response_model=ApplicationDetailOut)
def grant_consent(
    payload: ConsentRequest,
    application: Application = Depends(get_owned_application),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationDetailOut:
    updated = service.grant_consent(application, payload.consent_version)
    return _detail(service, updated)


@router.post("/{application_id}/submit", response_model=SubmitResponse)
def submit_application(
    payload: SubmitRequest,
    response: Response,
    application: Application = Depends(get_owned_application),
    service: ApplicationService = Depends(get_application_service),
    db: Session = Depends(get_db_dep),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> SubmitResponse:
    scope = f"submit:{application.id}"
    stored = load_idempotent_response(db, scope, idempotency_key)
    if stored is not None:
        response.headers["Idempotent-Replay"] = "true"
        return stored
    submitted = service.submit(application, actor=f"applicant:{application.id}")
    result = SubmitResponse(
        application=ApplicationOut.model_validate(submitted),
        message=(
            "Submitted for human review. KuralCredit does not make credit decisions; a human "
            "reviewer will review the packet."
        ),
    )
    store_idempotent_response(db, scope, idempotency_key, result.model_dump(mode="json"))
    return result


@router.post("/{application_id}/withdraw", response_model=ApplicationDetailOut)
def withdraw_application(
    payload: WithdrawRequest,
    application: Application = Depends(get_owned_application),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationDetailOut:
    updated = service.withdraw(
        application, actor=f"applicant:{application.id}", reason=payload.reason
    )
    return _detail(service, updated)


@router.delete("/{application_id}", response_model=DeleteResponse)
def delete_application(
    application: Application = Depends(get_owned_application),
    service: ApplicationService = Depends(get_application_service),
    storage: LocalStorage = Depends(get_storage_dep),
) -> DeleteResponse:
    deleted_id = application.id
    service.delete(application, actor=f"applicant:{deleted_id}", storage=storage)
    return DeleteResponse(
        message="Application data and uploaded files were deleted.",
        deleted_application_id=deleted_id,
    )
