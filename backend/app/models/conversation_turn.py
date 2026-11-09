from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class ConversationTurn(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversation_turns"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    input_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(60), nullable=True)
    target_field: Mapped[str | None] = mapped_column(String(80), nullable=True)
    question_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    linked_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correction_status: Mapped[str] = mapped_column(String(30), default="not_required")
