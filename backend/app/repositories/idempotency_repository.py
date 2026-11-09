from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, scope: str, key: str) -> IdempotencyRecord | None:
        return self.session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope == scope, IdempotencyRecord.key == key
            )
        )

    def put(self, scope: str, key: str, response_json: dict) -> IdempotencyRecord:
        record = IdempotencyRecord(scope=scope, key=key, response_json=response_json)
        self.session.add(record)
        self.session.flush()
        return record
