from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.core.lifecycle import ApplicationStatus
from app.models.base import Base, IdMixin, TimestampMixin


class CoerceInt(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None:
            return 1
        if isinstance(value, int):
            return value
        try:
            return int(str(value).split(".")[0])
        except (ValueError, TypeError):
            return 1

    def process_bind_param(self, value, dialect):
        if value is None:
            return 1
        if isinstance(value, int):
            return value
        try:
            return int(str(value).split(".")[0])
        except (ValueError, TypeError):
            return 1


class Application(Base, IdMixin, TimestampMixin):
    __tablename__ = "applications"

    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    workflow_id: Mapped[str] = mapped_column(
        String(60), default="loan_application", nullable=False, index=True
    )
    workflow_version: Mapped[int] = mapped_column(CoerceInt, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=ApplicationStatus.CONSENT_PENDING.value, nullable=False, index=True
    )
    applicant_name: Mapped[str] = mapped_column(String(120), nullable=False)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    voice: Mapped[str] = mapped_column(String(60), nullable=False)
    consent_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demo_scenario: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
