from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, document: Document) -> Document:
        self.session.add(document)
        self.session.flush()
        return document

    def get(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)

    def list_for_application(
        self, application_id: str, *, include_deleted: bool = False
    ) -> list[Document]:
        statement = select(Document).where(Document.application_id == application_id)
        if not include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        return list(self.session.scalars(statement.order_by(Document.created_at.asc())))
