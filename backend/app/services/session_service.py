from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_session_token, verify_demo_password
from app.models.application import Application
from app.models.base import utcnow
from app.models.session import SessionRecord
from app.repositories.session_repository import SessionRepository


@dataclass
class SessionContext:
    session_id: str
    role: str
    application_id: str | None
    display_name: str


@dataclass
class IssuedSession:
    token: str
    session_id: str
    expires_at: datetime
    display_name: str


class SessionService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = SessionRepository(db)

    def issue_applicant_session(self, application: Application) -> IssuedSession:
        expires_at = utcnow() + timedelta(hours=self.settings.session_ttl_hours)
        record = SessionRecord(
            role="applicant",
            application_id=application.id,
            workflow_id=getattr(application, "workflow_id", "loan_application"),
            display_name=application.applicant_name,
            expires_at=expires_at,
        )
        self.repository.add(record)
        token = create_session_token(
            session_id=record.id,
            role="applicant",
            application_id=application.id,
            secret_key=self.settings.secret_key,
            ttl_hours=self.settings.session_ttl_hours,
        )
        return IssuedSession(
            token=token,
            session_id=record.id,
            expires_at=expires_at,
            display_name=application.applicant_name,
        )

    def issue_reviewer_session(self, email: str, password: str) -> IssuedSession:
        if not self.settings.reviewer_login_configured:
            raise UnauthorizedError(
                "Reviewer demo login is not configured. Set REVIEWER_DEMO_EMAIL and "
                "REVIEWER_DEMO_PASSWORD in the backend environment."
            )
        expected_email = self.settings.reviewer_demo_email.strip().lower()
        expected_password = self.settings.reviewer_demo_password
        assert expected_password is not None
        if email.strip().lower() != expected_email or not verify_demo_password(
            password, expected_password.get_secret_value()
        ):
            raise UnauthorizedError("Invalid reviewer credentials")
        expires_at = utcnow() + timedelta(hours=self.settings.session_ttl_hours)
        record = SessionRecord(
            role="reviewer",
            application_id=None,
            display_name=self.settings.reviewer_display_name,
            expires_at=expires_at,
        )
        self.repository.add(record)
        token = create_session_token(
            session_id=record.id,
            role="reviewer",
            application_id=None,
            secret_key=self.settings.secret_key,
            ttl_hours=self.settings.session_ttl_hours,
        )
        return IssuedSession(
            token=token,
            session_id=record.id,
            expires_at=expires_at,
            display_name=self.settings.reviewer_display_name,
        )
