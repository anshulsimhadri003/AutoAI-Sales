from __future__ import annotations

from sqlalchemy.orm import Session

from shared.models.models import UserEvent
from shared.utils.ids import make_public_id


class UserEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: UserEvent) -> UserEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def next_public_id(self) -> str:
        return make_public_id("UE")

    def list_for_session(self, dealership_id: str, session_id: str):
        return (
            self.db.query(UserEvent)
            .filter(UserEvent.dealership_id == dealership_id, UserEvent.session_id == session_id)
            .order_by(UserEvent.id.asc())
            .all()
        )

    def get_latest_for_session(self, dealership_id: str, session_id: str) -> UserEvent | None:
        return (
            self.db.query(UserEvent)
            .filter(UserEvent.dealership_id == dealership_id, UserEvent.session_id == session_id)
            .order_by(UserEvent.id.desc())
            .first()
        )

    def get_latest_with_lead(self, dealership_id: str, session_id: str) -> UserEvent | None:
        return (
            self.db.query(UserEvent)
            .filter(
                UserEvent.dealership_id == dealership_id,
                UserEvent.session_id == session_id,
                UserEvent.lead_public_id.isnot(None),
            )
            .order_by(UserEvent.id.desc())
            .first()
        )
