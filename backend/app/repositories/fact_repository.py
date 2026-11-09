from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial_fact import FinancialFact


class FactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: FinancialFact) -> FinancialFact:
        self.session.add(fact)
        self.session.flush()
        return fact

    def get(self, fact_id: str) -> FinancialFact | None:
        return self.session.get(FinancialFact, fact_id)

    def list_for_application(
        self, application_id: str, *, include_rejected: bool = True
    ) -> list[FinancialFact]:
        statement = select(FinancialFact).where(FinancialFact.application_id == application_id)
        if not include_rejected:
            statement = statement.where(FinancialFact.provenance_status != "rejected")
        return list(self.session.scalars(statement.order_by(FinancialFact.created_at.asc())))

    def latest_for_field(self, application_id: str, field_key: str) -> FinancialFact | None:
        return self.session.scalar(
            select(FinancialFact)
            .where(
                FinancialFact.application_id == application_id,
                FinancialFact.field_key == field_key,
                FinancialFact.provenance_status != "rejected",
            )
            .order_by(FinancialFact.version.desc(), FinancialFact.created_at.desc())
            .limit(1)
        )
