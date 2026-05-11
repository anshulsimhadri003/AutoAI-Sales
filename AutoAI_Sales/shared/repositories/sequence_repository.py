from __future__ import annotations

from sqlalchemy.orm import Session

from shared.models.models import MessageEvent, Sequence
from shared.utils.ids import make_public_id


class SequenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, dealership_id: str):
        return (
            self.db.query(Sequence)
            .filter(Sequence.dealership_id == dealership_id)
            .order_by(Sequence.id.desc())
            .all()
        )

    def get_active_for_lead(self, dealership_id: str, lead_public_id: str):
        return (
            self.db.query(Sequence)
            .filter(
                Sequence.dealership_id == dealership_id,
                Sequence.lead_public_id == lead_public_id,
                Sequence.status.in_(["Active", "Paused", "Escalated"]),
            )
            .order_by(Sequence.id.desc())
            .first()
        )

    def create(self, sequence: Sequence):
        self.db.add(sequence)
        self.db.commit()
        self.db.refresh(sequence)
        return sequence

    def save(self, sequence: Sequence):
        self.db.add(sequence)
        self.db.commit()
        self.db.refresh(sequence)
        return sequence

    def create_message_event(self, event: MessageEvent):
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_message_events(self, dealership_id: str):
        return (
            self.db.query(MessageEvent)
            .filter(MessageEvent.dealership_id == dealership_id)
            .order_by(MessageEvent.id.desc())
            .all()
        )

    def list_message_events_for_lead(self, dealership_id: str, lead_public_id: str):
        return (
            self.db.query(MessageEvent)
            .filter(
                MessageEvent.dealership_id == dealership_id,
                MessageEvent.lead_public_id == lead_public_id,
            )
            .order_by(MessageEvent.id.desc())
            .all()
        )

    def next_public_id(self, dealership_id: str) -> str:
        return make_public_id("SEQ")
