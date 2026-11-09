from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.session import SessionRecord


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, record: SessionRecord) -> SessionRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, session_id: str) -> SessionRecord | None:
        return self.session.get(SessionRecord, session_id)
