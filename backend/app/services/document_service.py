from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ProviderError,
    ValidationAppError,
)
from app.core.security import compute_sha256, sanitize_filename
from app.document_parsers.parser_registry import get_parser
from app.document_parsers.profiles import detect_document_type, get_profile
from app.document_parsers.table_extractor import extract_profile_facts
from app.domain.application_state import is_editable_by_applicant
from app.domain.provenance import ExtractionMethod, ProvenanceStatus
from app.models.application import Application
from app.models.document import Document
from app.models.financial_fact import FinancialFact
from app.repositories.document_repository import DocumentRepository
from app.repositories.fact_repository import FactRepository
from app.schemas.document import DocumentListOut, DocumentUploadOut
from app.services.audit_service import AuditService
from app.services.evidence_service import EvidenceService
from app.services.extraction_service import ExtractionService, document_target_fields
from app.services.serializers import document_out
from app.storage.base import StorageProvider
from app.storage.file_validation import validate_document

logger = logging.getLogger(__name__)

DOCUMENT_TYPE_ALIASES = {
    "bank": "bank_statement",
    "bank_statement": "bank_statement",
    "gst": "gst_summary",
    "gst_summary": "gst_summary",
    "gst_return": "gst_summary",
    "sales": "sales_register",
    "sales_register": "sales_register",
    "other": "other",
}
SUPPORTED_DOCUMENT_TYPES = frozenset({"bank_statement", "gst_summary", "sales_register", "other"})


class DocumentService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        storage: StorageProvider,
        extraction: ExtractionService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage
        self.extraction = extraction
        self.documents = DocumentRepository(db)
        self.facts = FactRepository(db)
        self.evidence = EvidenceService(db)
        self.audit = AuditService(db)

    def upload(
        self,
        application: Application,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        document_type: str | None,
        actor: str,
    ) -> DocumentUploadOut:
        if not is_editable_by_applicant(application.status):
            raise ConflictError("Documents cannot be added in the current application state")
        safe_name = sanitize_filename(filename)
        suffix = validate_document(
            safe_name,
            content,
            content_type,
            allowed_extensions=self.settings.allowed_document_suffixes,
            max_size_bytes=self.settings.max_upload_size_bytes,
        )
        parser = get_parser(suffix)
        parsed = None
        parse_error: str | None = None
        try:
            parsed = parser.parse(content)
        except ValidationAppError as exc:
            parse_error = exc.message
        resolved_type = self._resolve_document_type(document_type, safe_name, parsed, suffix)
        profile = None
        if resolved_type in SUPPORTED_DOCUMENT_TYPES and resolved_type != "other":
            profile = get_profile(resolved_type)
        stored_filename, _ = self.storage.save(application.id, safe_name, content)
        document = Document(
            application_id=application.id,
            original_filename=safe_name,
            stored_filename=stored_filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(content),
            sha256=compute_sha256(content),
            document_type=resolved_type,
            parser_profile=profile.document_type if profile else "none",
            status="uploaded",
            metadata_json={
                "requested_document_type": document_type,
                "detected_document_type": resolved_type,
                "extension": suffix,
            },
        )
        self.documents.add(document)
        if parse_error:
            document.status = "parse_failed"
            document.parse_notes = parse_error
            self.audit.record(
                application_id=application.id,
                actor=actor,
                event_type="document_uploaded",
                summary="Document uploaded but could not be parsed.",
                detail={
                    "document_id": document.id,
                    "document_type": resolved_type,
                    "status": document.status,
                },
            )
            self.db.commit()
            return DocumentUploadOut(
                document=document_out(document),
                facts_created=0,
                extraction_notes=[parse_error],
            )
        assert parsed is not None
        document.page_count = parsed.page_count
        document.metadata_json = {
            **(document.metadata_json or {}),
            "table_count": len(parsed.tables),
            "headers": [table.headers for table in parsed.tables][:3],
            "parser": parser.name,
        }
        notes = list(parsed.notes)
        facts: list[FinancialFact] = []
        if profile is not None and parsed.tables:
            outcome = extract_profile_facts(parsed, profile)
            notes.extend(outcome.notes)
            for draft in outcome.facts:
                try:
                    fact_draft = self.evidence.build_draft(
                        field_key=draft.field_key,
                        raw_value=draft.raw_value,
                        normalized_candidate=draft.normalized_value,
                        currency=draft.currency,
                        period_start=draft.period_start,
                        period_end=draft.period_end,
                        source_type=draft.source_type,
                        provenance_status=ProvenanceStatus.DOCUMENT_EXTRACTED.value,
                        extraction_method=ExtractionMethod.DOCUMENT_PARSER.value,
                        source_document_id=document.id,
                        source_locator=draft.source_locator,
                        confidence_estimate=0.9,
                        notes=draft.notes,
                        measure_type_override=draft.measure_type,
                        apply_default_period=False,
                    )
                except ValidationAppError as exc:
                    notes.append(f"{draft.field_key}: {exc.message}")
                    continue
                if self.extraction._duplicate_exists(application.id, fact_draft):
                    notes.append(f"{draft.field_key}: duplicate value ignored.")
                    continue
                facts.append(self.evidence.create_fact(application.id, fact_draft))
            if outcome.status == "failed" and not facts:
                notes.extend(outcome.notes)
        elif parsed.readable:
            try:
                model_facts, model_notes, _ = self.extraction.extract_document_with_model(
                    application,
                    document,
                    parsed.text,
                    parsed.locators,
                    document_target_fields(resolved_type),
                )
                facts.extend(model_facts)
                notes.extend(model_notes)
            except ProviderError as exc:
                notes.append(
                    "Model-assisted extraction was unavailable, so no values were extracted "
                    f"from this document ({exc.code}). The document is still stored as evidence."
                )
                logger.warning(
                    "document_model_extraction_failed",
                    extra={"extra_fields": {"document_id": document.id, "error_code": exc.code}},
                )
        else:
            notes.extend(parsed.notes or ["The document has no readable content."])

        self.evidence.record_batch_audit(
            application.id,
            actor=actor,
            facts=facts,
            source_label=f"document {document.original_filename}",
        )
        if facts:
            document.status = "parsed"
        elif parsed.readable:
            document.status = "parsed_with_warnings"
        else:
            document.status = "parse_failed"
        document.parse_notes = "; ".join(dict.fromkeys(notes)) or None
        document.metadata_json = {
            **(document.metadata_json or {}),
            "facts_created": len(facts),
            "field_keys": sorted({fact.field_key for fact in facts}),
        }
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="document_uploaded",
            summary="Document uploaded and processed. Values require applicant confirmation.",
            detail={
                "document_id": document.id,
                "document_type": resolved_type,
                "status": document.status,
                "facts_created": len(facts),
                "sha256_prefix": document.sha256[:12],
            },
        )
        self.db.commit()
        return DocumentUploadOut(
            document=document_out(document),
            facts_created=len(facts),
            extraction_notes=notes,
        )

    def list_documents(self, application_id: str) -> DocumentListOut:
        return DocumentListOut(
            items=[
                document_out(document)
                for document in self.documents.list_for_application(application_id)
            ]
        )

    def get_document(self, document_id: str) -> Document:
        document = self.documents.get(document_id)
        if document is None or document.deleted_at is not None:
            raise NotFoundError("Document not found")
        return document

    def delete(self, document: Document, application: Application, actor: str) -> None:
        if not is_editable_by_applicant(application.status):
            raise ConflictError("Documents cannot be deleted in the current application state")
        try:
            self.storage.delete(document.stored_filename)
        except Exception:
            logger.warning(
                "document_file_delete_failed",
                extra={"extra_fields": {"document_id": document.id}},
            )
        from app.models.base import utcnow

        document.deleted_at = utcnow()
        document.status = "deleted"
        for fact in self.facts.list_for_application(application.id, include_rejected=False):
            if fact.source_document_id != document.id:
                continue
            fact.provenance_status = ProvenanceStatus.REJECTED.value
            fact.notes = (
                f"{fact.notes}; " if fact.notes else ""
            ) + "Source document was deleted by the applicant."
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="document_deleted",
            summary="Applicant deleted a document. Facts derived from it were rejected.",
            detail={"document_id": document.id, "document_type": document.document_type},
        )
        self.db.commit()

    def _resolve_document_type(
        self,
        requested: str | None,
        filename: str,
        parsed,
        suffix: str,
    ) -> str:
        if requested:
            normalized = DOCUMENT_TYPE_ALIASES.get(requested.strip().lower())
            if normalized is None:
                raise ValidationAppError(
                    "document_type must be bank_statement, gst_summary, sales_register or other"
                )
            return normalized
        if parsed is not None and parsed.tables:
            detected = detect_document_type(parsed.tables[0].headers)
            if detected:
                return DOCUMENT_TYPE_ALIASES.get(detected, detected)
        lowered = Path(filename).stem.lower()
        if "bank" in lowered or "statement" in lowered:
            return "bank_statement"
        if "gst" in lowered:
            return "gst_summary"
        if "sales" in lowered or "register" in lowered:
            return "sales_register"
        return "other"
