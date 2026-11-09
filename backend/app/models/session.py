from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class SessionRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "sessions"

    role: Mapped[str] = mapped_column(String(20), nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def is_active(self) -> bool:
        now = utcnow()
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=now.tzinfo)
        return self.revoked_at is None and expires > now
