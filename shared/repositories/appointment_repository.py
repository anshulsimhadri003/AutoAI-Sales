from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from shared.models.models import Appointment
from shared.utils.ids import make_public_id


class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, dealership_id: str):
        return (
            self.db.query(Appointment)
            .filter(Appointment.dealership_id == dealership_id)
            .order_by(Appointment.id.desc())
            .all()
        )

    def get_by_public_id(self, dealership_id: str, public_id: str):
        return (
            self.db.query(Appointment)
            .filter(Appointment.dealership_id == dealership_id, Appointment.public_id == public_id)
            .first()
        )

    def create(self, appointment: Appointment):
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def save(self, appointment: Appointment):
        appointment.updated_at = datetime.utcnow()
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def list_by_rep_and_date(self, dealership_id: str, rep_id: str, date: str):
        return (
            self.db.query(Appointment)
            .filter(
                Appointment.dealership_id == dealership_id,
                Appointment.rep_id == rep_id,
                Appointment.start_time.startswith(date),
                Appointment.status.in_(["Confirmed", "Rescheduled"]),
            )
            .all()
        )

    def next_public_id(self, dealership_id: str) -> str:
        return make_public_id("AP")
