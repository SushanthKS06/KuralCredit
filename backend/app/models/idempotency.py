from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class IdempotencyRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "idempotency_records"

    scope: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
