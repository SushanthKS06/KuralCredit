from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.lifecycle import ApplicationStatus, assert_transition
from app.domain.application_state import is_editable_by_applicant
from app.domain.provenance import is_confirmed
from app.models.application import Application
from app.models.base import utcnow
from app.providers.gnani.capability_catalog import CapabilityCatalog
from app.repositories.application_repository import ApplicationRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.fact_repository import FactRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    CompletenessItem,
    CompletenessOut,
)
from app.services.audit_service import AuditService
from app.services.session_service import IssuedSession, SessionService

FIELD_LABELS = {
    "business_name": "Registered business name",
    "business_type": "Business type",
    "annual_sales": "Declared annual sales (FY2025-26)",
    "gst_turnover": "GST turnover (FY2025-26)",
    "bank_credits": "Bank statement credits",
}


class ApplicationService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        catalog: CapabilityCatalog,
    ) -> None:
        self.db = db
        self.settings = settings
        self.catalog = catalog
        self.applications = ApplicationRepository(db)
        self.facts = FactRepository(db)
        self.documents = DocumentRepository(db)
        self.conversations = ConversationRepository(db)
        self.audit = AuditService(db)

    def create_application(
        self, payload: ApplicationCreate
    ) -> tuple[Application, CompletenessOut, IssuedSession]:
        self._validate_language_voice(payload.language, payload.voice)
        workflow_id = getattr(payload, "workflow_id", None) or "loan_application"
        from app.domain.workflow.registry import get_workflow_registry

        wf = get_workflow_registry().get(workflow_id)

        application = Application(
            reference=self._new_reference(),
            workflow_id=wf.workflow_id,
            workflow_version=wf.workflow_version,
            status=ApplicationStatus.CONSENT_PENDING.value,
            applicant_name=payload.applicant_name.strip(),
            business_name=payload.business_name.strip(),
            language=payload.language,
            voice=payload.voice,
            is_demo=False,
        )
        self.applications.add(application)
        self.audit.record(
            application_id=application.id,
            actor=f"applicant:{application.id}",
            event_type="application_created",
            summary=f"Application created for workflow '{wf.workflow_id}' v{wf.workflow_version}.",
            detail={
                "language": payload.language,
                "voice": payload.voice,
                "workflow_id": wf.workflow_id,
                "workflow_version": wf.workflow_version,
            },
        )
        self._grant_consent(application, payload.consent_version)
        session = SessionService(self.db, self.settings).issue_applicant_session(application)
        self.db.commit()
        return application, self.completeness(application), session

    def _grant_consent(self, application: Application, consent_version: str) -> None:
        from app.domain.workflow.registry import get_workflow_registry

        wf = get_workflow_registry().get(
            getattr(application, "workflow_id", "loan_application"),
            getattr(application, "workflow_version", 1),
        )
        initial_target = ApplicationStatus(wf.initial_stage)
        assert_transition(application.status, initial_target)
        application.status = initial_target.value
        application.consent_version = consent_version
        application.consent_given_at = utcnow()
        self.audit.record(
            application_id=application.id,
            actor=f"applicant:{application.id}",
            event_type="consent_granted",
            summary="Applicant granted explicit consent for processing.",
            detail={"consent_version": consent_version, "stage": initial_target.value},
        )

    def grant_consent(self, application: Application, consent_version: str) -> Application:
        if ApplicationStatus(application.status) != ApplicationStatus.CONSENT_PENDING:
            raise ConflictError("Consent has already been recorded for this application")
        self._grant_consent(application, consent_version)
        self.db.commit()
        return application

    def update_application(
        self, application: Application, payload: ApplicationUpdate, actor: str
    ) -> Application:
        if not is_editable_by_applicant(application.status):
            raise ConflictError("This application can no longer be edited")
        changes: dict[str, str] = {}
        if payload.language is not None or payload.voice is not None:
            language = payload.language or application.language
            voice = payload.voice or application.voice
            self._validate_language_voice(language, voice)
            if language != application.language:
                changes["language"] = language
            if voice != application.voice:
                changes["voice"] = voice
            application.language = language
            application.voice = voice
        if payload.business_name is not None and payload.business_name != application.business_name:
            changes["business_name"] = payload.business_name
            application.business_name = payload.business_name.strip()
        if payload.business_type is not None and payload.business_type != application.business_type:
            changes["business_type"] = payload.business_type
            application.business_type = payload.business_type.strip() or None
        if changes:
            self.audit.record(
                application_id=application.id,
                actor=actor,
                event_type="application_updated",
                summary="Application details updated.",
                detail={"changed_fields": sorted(changes.keys())},
            )
            self.db.commit()
        return application

    def completeness(self, application: Application) -> CompletenessOut:
        items: list[CompletenessItem] = []
        missing_fields: list[str] = []
        unconfirmed_fields: list[str] = []

        from app.domain.workflow.registry import get_workflow_registry

        wf = get_workflow_registry().get(
            getattr(application, "workflow_id", "loan_application"),
            getattr(application, "workflow_version", 1),
        )

        for field_def in wf.fields:
            if not field_def.required:
                continue
            field_key = field_def.id
            label = field_def.label
            if field_key == "business_name":
                complete = bool(application.business_name.strip())
                detail = "Provided at consent." if complete else "Business name is missing."
                items.append(
                    CompletenessItem(key=field_key, label=label, complete=complete, detail=detail)
                )
                if not complete:
                    missing_fields.append(field_key)
                continue
            fact = self.facts.latest_for_field(application.id, field_key)
            if fact is None:
                missing_fields.append(field_key)
                items.append(
                    CompletenessItem(
                        key=field_key,
                        label=label,
                        complete=False,
                        detail="No value recorded yet.",
                    )
                )
                continue
            if not is_confirmed(fact.provenance_status):
                unconfirmed_fields.append(field_key)
                items.append(
                    CompletenessItem(
                        key=field_key,
                        label=label,
                        complete=False,
                        detail="Value exists but has not been confirmed by the applicant.",
                    )
                )
                continue
            items.append(
                CompletenessItem(
                    key=field_key,
                    label=label,
                    complete=True,
                    detail="Applicant-confirmed value.",
                )
            )

        documents = [
            document
            for document in self.documents.list_for_application(application.id)
            if document.deleted_at is None
        ]
        missing_documents: list[str] = []
        for doc_profile in wf.document_profiles:
            if not doc_profile.required:
                continue
            document_type = doc_profile.id
            candidates = [doc for doc in documents if doc.document_type == document_type]
            parsed = [doc for doc in candidates if doc.status in {"parsed", "parsed_with_warnings"}]
            complete = bool(parsed)
            if not complete:
                missing_documents.append(document_type)
            detail = (
                "Parsed document is attached."
                if complete
                else (
                    "Document uploaded but parsing failed."
                    if candidates
                    else f"No {doc_profile.label.lower()} has been uploaded."
                )
            )
            items.append(
                CompletenessItem(
                    key=f"document:{document_type}",
                    label=doc_profile.label,
                    complete=complete,
                    detail=detail,
                )
            )

        open_clarifications = len(
            self.conversations.list_clarifications(application.id, status="open")
        )
        items.append(
            CompletenessItem(
                key="clarifications",
                label="Open clarification questions",
                complete=open_clarifications == 0,
                detail=(
                    "No open questions."
                    if open_clarifications == 0
                    else f"{open_clarifications} question(s) still need an answer."
                ),
            )
        )

        status_allows_submit = ApplicationStatus(application.status) in {
            ApplicationStatus.APPLICANT_REVIEW,
            ApplicationStatus.NEEDS_MORE_INFORMATION,
        }
        can_submit = (
            status_allows_submit
            and not missing_fields
            and not unconfirmed_fields
            and not missing_documents
            and open_clarifications == 0
        )
        return CompletenessOut(
            can_submit=can_submit,
            missing_fields=missing_fields,
            unconfirmed_fields=unconfirmed_fields,
            missing_documents=missing_documents,
            open_clarifications=open_clarifications,
            items=items,
        )

    def submit(self, application: Application, actor: str) -> Application:
        status = ApplicationStatus(application.status)
        if status not in {
            ApplicationStatus.APPLICANT_REVIEW,
            ApplicationStatus.NEEDS_MORE_INFORMATION,
        }:
            raise ConflictError(
                "The application can only be submitted from applicant review or after a "
                "reviewer information request"
            )
        completeness = self.completeness(application)
        if not completeness.can_submit:
            raise ConflictError(
                "The application is not ready for submission",
                details=completeness.model_dump(),
            )
        assert_transition(application.status, ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW)
        application.status = ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW.value
        application.submitted_at = utcnow()
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="application_submitted",
            summary="Applicant submitted the packet for human review. No credit decision was made.",
            detail={"completeness": completeness.model_dump()},
        )
        self.db.commit()
        return application

    def withdraw(self, application: Application, actor: str, reason: str) -> Application:
        assert_transition(application.status, ApplicationStatus.WITHDRAWN)
        application.status = ApplicationStatus.WITHDRAWN.value
        application.withdrawn_at = utcnow()
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="application_withdrawn",
            summary="Applicant withdrew the application.",
            detail={"reason": reason},
        )
        self.db.commit()
        return application

    def delete(self, application: Application, actor: str, storage) -> None:
        if ApplicationStatus(application.status) in {
            ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
            ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS,
            ApplicationStatus.REVIEW_COMPLETED,
        }:
            raise ConflictError(
                "An application under human review cannot be deleted through this demo endpoint"
            )
        documents = self.documents.list_for_application(application.id, include_deleted=True)
        for document in documents:
            try:
                storage.delete(document.stored_filename)
            except Exception:
                pass
        self.audit.record(
            application_id=None,
            actor=actor,
            event_type="application_deleted",
            summary="Application data deleted at applicant request.",
            detail={"reference": application.reference},
        )
        self.db.delete(application)
        self.db.commit()

    def get_application(self, application_id: str) -> Application:
        application = self.applications.get(application_id)
        if application is None:
            raise NotFoundError("Application not found")
        return application

    def list_applications(
        self,
        *,
        status: str | None,
        query: str | None,
        limit: int,
        offset: int,
        application_id: str | None = None,
    ) -> tuple[list[Application], int]:
        if application_id:
            application = self.applications.get(application_id)
            if application is None:
                raise NotFoundError("Application not found")
            return [application], 1
        return self.applications.list(status=status, query=query, limit=limit, offset=offset)

    def _validate_language_voice(self, language: str, voice: str) -> None:
        if self.catalog.stt_language(language) is None:
            raise ValidationAppError(
                f"Language '{language}' is not supported for the voice interview"
            )
        self.catalog.validate_voice(language, voice, self.settings.gnani_tts_model)

    def _new_reference(self) -> str:
        prefix = datetime.now(UTC).strftime("KC%y%m")
        for _ in range(10):
            reference = f"{prefix}-{secrets.token_hex(4).upper()}"
            if self.applications.get_by_reference(reference) is None:
                return reference
        raise ConflictError("Could not allocate a unique application reference")
