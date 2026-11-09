from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    enforce_rate_limit,
    get_current_session,
    get_db_dep,
    get_document_service,
    get_owned_application,
    get_readable_application,
    get_settings_dep,
    get_storage_dep,
    require_applicant,
)
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models.application import Application
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.schemas.common import MessageResponse
from app.schemas.document import DocumentListOut, DocumentUploadOut
from app.services.document_service import DocumentService
from app.services.session_service import SessionContext
from app.storage.local_storage import LocalStorage

router = APIRouter(tags=["documents"])

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _readable_document(
    document_id: str,
    session: SessionContext,
    db: Session,
) -> Document:
    document = DocumentRepository(db).get(document_id)
    if document is None or document.deleted_at is not None:
        raise NotFoundError("Document not found")
    if session.role == "applicant" and session.application_id != document.application_id:
        raise ForbiddenError("You can only access documents from your own application")
    return document


@router.post(
    "/applications/{application_id}/documents",
    response_model=DocumentUploadOut,
    status_code=201,
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str | None = Form(default=None),
    application: Application = Depends(get_owned_application),
    session: SessionContext = Depends(require_applicant),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadOut:
    enforce_rate_limit("document_upload", session, settings)
    max_bytes = settings.max_upload_size_bytes
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValidationAppError(
            f"Document exceeds the configured limit of {settings.max_upload_size_mb} MB"
        )
    return service.upload(
        application,
        filename=file.filename or "document",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        document_type=document_type,
        actor=f"applicant:{application.id}",
    )


@router.get("/applications/{application_id}/documents", response_model=DocumentListOut)
def list_documents(
    application: Application = Depends(get_readable_application),
    service: DocumentService = Depends(get_document_service),
) -> DocumentListOut:
    return service.list_documents(application.id)


@router.get("/documents/{document_id}/file")
def document_file(
    document_id: str,
    session: SessionContext = Depends(get_current_session),
    db: Session = Depends(get_db_dep),
    storage: LocalStorage = Depends(get_storage_dep),
) -> FileResponse:
    document = _readable_document(document_id, session, db)
    path = storage.path_for(document.stored_filename)
    if not Path(path).exists():
        raise NotFoundError("The stored document file is unavailable")
    media_type = MEDIA_TYPES.get(Path(document.stored_filename).suffix.lower())
    if media_type is None:
        raise ValidationAppError("This document type cannot be previewed")
    return FileResponse(
        path,
        media_type=media_type,
        filename=document.original_filename,
        content_disposition_type="inline" if media_type == "application/pdf" else "attachment",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: str,
    session: SessionContext = Depends(require_applicant),
    db: Session = Depends(get_db_dep),
    service: DocumentService = Depends(get_document_service),
) -> MessageResponse:
    document = _readable_document(document_id, session, db)
    if session.application_id != document.application_id:
        raise ForbiddenError("You can only delete documents from your own application")
    application = db.get(Application, document.application_id)
    if application is None:
        raise NotFoundError("Application not found")
    service.delete(document, application, actor=f"applicant:{application.id}")
    return MessageResponse(message="Document deleted and derived facts were rejected.")
