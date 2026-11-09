from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.clarification import Clarification
from app.models.conversation_turn import ConversationTurn


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_turn(self, turn: ConversationTurn) -> ConversationTurn:
        self.session.add(turn)
        self.session.flush()
        return turn

    def next_turn_index(self, application_id: str) -> int:
        current = self.session.scalar(
            select(func.max(ConversationTurn.turn_index)).where(
                ConversationTurn.application_id == application_id
            )
        )
        return int(current or 0) + 1

    def list_turns(self, application_id: str) -> list[ConversationTurn]:
        return list(
            self.session.scalars(
                select(ConversationTurn)
                .where(ConversationTurn.application_id == application_id)
                .order_by(ConversationTurn.turn_index.asc())
            )
        )

    def add_clarification(self, clarification: Clarification) -> Clarification:
        self.session.add(clarification)
        self.session.flush()
        return clarification

    def get_clarification(self, clarification_id: str) -> Clarification | None:
        return self.session.get(Clarification, clarification_id)

    def list_clarifications(
        self, application_id: str, *, status: str | None = None
    ) -> list[Clarification]:
        statement = select(Clarification).where(Clarification.application_id == application_id)
        if status:
            statement = statement.where(Clarification.status == status)
        return list(
            self.session.scalars(
                statement.order_by(Clarification.priority.asc(), Clarification.created_at.asc())
            )
        )

    def open_clarification_for_field(
        self, application_id: str, field_key: str
    ) -> Clarification | None:
        return self.session.scalar(
            select(Clarification)
            .where(
                Clarification.application_id == application_id,
                Clarification.field_key == field_key,
                Clarification.status == "open",
            )
            .order_by(Clarification.priority.asc())
            .limit(1)
        )

    def next_open_clarification(self, application_id: str) -> Clarification | None:
        return self.session.scalar(
            select(Clarification)
            .where(
                Clarification.application_id == application_id,
                Clarification.status == "open",
            )
            .order_by(Clarification.priority.asc(), Clarification.created_at.asc())
            .limit(1)
        )
