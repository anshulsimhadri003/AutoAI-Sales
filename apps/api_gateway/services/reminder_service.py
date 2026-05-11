from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from shared.models.models import Appointment, AppointmentReminder


class ReminderService:
    def __init__(self, db: Session):
        self.db = db

    def schedule_for_appointment(self, appointment: Appointment) -> list[AppointmentReminder]:
        start_dt = datetime.fromisoformat(appointment.start_time)
        reminders = [
            AppointmentReminder(
                dealership_id=appointment.dealership_id,
                appointment_public_id=appointment.public_id,
                reminder_type="24h",
                channel=appointment.channel,
                due_at=start_dt - timedelta(hours=24),
                status="scheduled",
            ),
            AppointmentReminder(
                dealership_id=appointment.dealership_id,
                appointment_public_id=appointment.public_id,
                reminder_type="2h",
                channel=appointment.channel,
                due_at=start_dt - timedelta(hours=2),
                status="scheduled",
            ),
        ]
        self.db.add_all(reminders)
        self.db.commit()
        return reminders
