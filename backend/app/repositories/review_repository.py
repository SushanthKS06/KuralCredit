from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.review import ReviewAction


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_action(self, action: ReviewAction) -> ReviewAction:
        self.session.add(action)
        self.session.flush()
        return action

    def list_actions(self, application_id: str) -> list[ReviewAction]:
        return list(
            self.session.scalars(
                select(ReviewAction)
                .where(ReviewAction.application_id == application_id)
                .order_by(ReviewAction.created_at.asc())
            )
        )

    def queue(
        self,
        *,
        statuses: set[str],
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Application]:
        statement = select(Application).where(Application.status.in_(statuses))
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                Application.reference.ilike(pattern)
                | Application.applicant_name.ilike(pattern)
                | Application.business_name.ilike(pattern)
            )
        return list(
            self.session.scalars(
                statement.order_by(Application.submitted_at.desc(), Application.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    def queue_count(
        self,
        *,
        statuses: set[str],
        query: str | None = None,
    ) -> int:
        statement = (
            select(func.count()).select_from(Application).where(Application.status.in_(statuses))
        )
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                Application.reference.ilike(pattern)
                | Application.applicant_name.ilike(pattern)
                | Application.business_name.ilike(pattern)
            )
        return int(self.session.scalar(statement) or 0)
