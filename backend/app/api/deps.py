from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.constants import IDEMPOTENCY_HEADER
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationAppError
from app.core.security import InMemoryRateLimiter, decode_session_token
from app.db.session import get_db
from app.models.application import Application
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.providers.registry import ProviderRegistry, get_catalog, get_registry
from app.repositories.application_repository import ApplicationRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.session_repository import SessionRepository
from app.services.application_service import ApplicationService
from app.services.conversation_service import ConversationService
from app.services.document_service import DocumentService
from app.services.extraction_service import ExtractionService
from app.services.reconciliation_service import ReconciliationService
from app.services.review_service import ReviewService
from app.services.session_service import SessionContext
from app.storage.local_storage import LocalStorage

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_dep() -> Settings:
    return get_settings()


def get_db_dep() -> Generator[Session, None, None]:
    yield from get_db()


def get_registry_dep() -> ProviderRegistry:
    return get_registry()


def get_catalog_dep() -> CapabilityCatalog:
    return get_catalog()


def get_storage_dep(settings: Settings = Depends(get_settings_dep)) -> LocalStorage:
    return LocalStorage(settings.upload_path)


@lru_cache
def _rate_limiter(limit: int) -> InMemoryRateLimiter:
    return InMemoryRateLimiter(limit)


def enforce_rate_limit(
    scope: str,
    session: SessionContext,
    settings: Settings,
) -> None:
    _rate_limiter(settings.rate_limit_per_minute).check(f"{scope}:{session.session_id}")


def enforce_public_rate_limit(scope: str, request: Request, settings: Settings) -> None:
    host = request.client.host if request.client else "unknown"
    _rate_limiter(settings.rate_limit_per_minute).check(f"{scope}:{host}")


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
) -> SessionContext:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication is required")
    payload = decode_session_token(credentials.credentials, settings.secret_key)
    session_id = payload.get("sub")
    if not isinstance(session_id, str) or not session_id:
        raise UnauthorizedError("Invalid session token")
    record = SessionRepository(db).get(session_id)
    if record is None or not record.is_active():
        raise UnauthorizedError("Session is not active")
    role = str(payload.get("role") or record.role)
    if role != record.role:
        raise UnauthorizedError("Session role mismatch")
    application_id = payload.get("app_id")
    if application_id != record.application_id:
        raise UnauthorizedError("Session application mismatch")
    return SessionContext(
        session_id=record.id,
        role=record.role,
        application_id=record.application_id,
        display_name=record.display_name,
    )


def require_applicant(
    session: SessionContext = Depends(get_current_session),
) -> SessionContext:
    if session.role != "applicant":
        raise ForbiddenError("This endpoint is for applicants only")
    return session


def require_reviewer(
    session: SessionContext = Depends(get_current_session),
) -> SessionContext:
    if session.role != "reviewer":
        raise ForbiddenError("This endpoint is for reviewers only")
    return session


def get_owned_application(
    application_id: str,
    session: SessionContext = Depends(require_applicant),
    db: Session = Depends(get_db_dep),
) -> Application:
    if session.application_id != application_id:
        raise ForbiddenError("You can only access your own application")
    application = ApplicationRepository(db).get(application_id)
    if application is None:
        raise NotFoundError("Application not found")
    return application


def get_readable_application(
    application_id: str,
    session: SessionContext = Depends(get_current_session),
    db: Session = Depends(get_db_dep),
) -> Application:
    if session.role == "applicant" and session.application_id != application_id:
        raise ForbiddenError("You can only access your own application")
    application = ApplicationRepository(db).get(application_id)
    if application is None:
        raise NotFoundError("Application not found")
    return application


def get_reviewer_application(
    application_id: str,
    session: SessionContext = Depends(require_reviewer),
    db: Session = Depends(get_db_dep),
) -> Application:
    application = ApplicationRepository(db).get(application_id)
    if application is None:
        raise NotFoundError("Application not found")
    return application


def get_application_service(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    catalog: CapabilityCatalog = Depends(get_catalog_dep),
) -> ApplicationService:
    return ApplicationService(db, settings, catalog)


def get_reconciliation_service(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
) -> ReconciliationService:
    return ReconciliationService(db, settings.reconciliation_tolerance_percent)


def get_extraction_service(
    db: Session = Depends(get_db_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
) -> ExtractionService:
    return ExtractionService(db, registry.reasoning)


def get_conversation_service(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
) -> ConversationService:
    return ConversationService(db, settings, registry.reasoning)


def get_document_service(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    storage: LocalStorage = Depends(get_storage_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
) -> DocumentService:
    return DocumentService(db, settings, storage, ExtractionService(db, registry.reasoning))


def get_review_service(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
    catalog: CapabilityCatalog = Depends(get_catalog_dep),
    application_service: ApplicationService = Depends(get_application_service),
) -> ReviewService:
    return ReviewService(db, settings, registry.reasoning, application_service)


def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
) -> str | None:
    if idempotency_key is None:
        return None
    cleaned = idempotency_key.strip()
    if not cleaned:
        return None
    if len(cleaned) > 120:
        raise ValidationAppError("Idempotency-Key must be at most 120 characters")
    return cleaned


def load_idempotent_response(db: Session, scope: str, key: str | None) -> dict | None:
    if not key:
        return None
    record = IdempotencyRepository(db).get(scope, key)
    return record.response_json if record is not None else None


def store_idempotent_response(db: Session, scope: str, key: str | None, payload: dict) -> None:
    if not key:
        return
    IdempotencyRepository(db).put(scope, key, payload)
    db.commit()
