from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Clarification(Base, IdMixin, TimestampMixin):
    __tablename__ = "clarifications"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer_type: Mapped[str] = mapped_column(String(40), default="text", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="rule", nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answer_turn_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
