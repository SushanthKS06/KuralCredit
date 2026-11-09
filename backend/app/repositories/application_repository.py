from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application


class ApplicationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, application: Application) -> Application:
        self.session.add(application)
        self.session.flush()
        return application

    def get(self, application_id: str) -> Application | None:
        return self.session.get(Application, application_id)

    def get_by_reference(self, reference: str) -> Application | None:
        return self.session.scalar(select(Application).where(Application.reference == reference))

    def list(
        self,
        *,
        status: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        statement = select(Application)
        count_statement = select(func.count()).select_from(Application)
        if status:
            statement = statement.where(Application.status == status)
            count_statement = count_statement.where(Application.status == status)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                Application.reference.ilike(pattern)
                | Application.applicant_name.ilike(pattern)
                | Application.business_name.ilike(pattern)
            )
            count_statement = count_statement.where(
                Application.reference.ilike(pattern)
                | Application.applicant_name.ilike(pattern)
                | Application.business_name.ilike(pattern)
            )
        total = int(self.session.scalar(count_statement) or 0)
        items = list(
            self.session.scalars(
                statement.order_by(Application.created_at.desc()).limit(limit).offset(offset)
            )
        )
        return items, total

    def delete_all(self) -> None:
        for application in self.session.scalars(select(Application)):
            self.session.delete(application)
        self.session.flush()
