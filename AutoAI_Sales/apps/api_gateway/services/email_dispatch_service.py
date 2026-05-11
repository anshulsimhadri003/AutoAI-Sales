from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.integrations.email_client import EmailClient
from shared.models.models import Appointment, AppointmentReminder
from shared.repositories.lead_repository import LeadRepository

logger = logging.getLogger(__name__)


class EmailDispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.email = EmailClient()
        self.leads = LeadRepository(db)

    def send_due_appointment_reminders(self, dealership_id: str | None = None) -> dict:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        query = (
            self.db.query(AppointmentReminder)
            .filter(
                AppointmentReminder.channel == "email",
                AppointmentReminder.status == "scheduled",
                AppointmentReminder.due_at <= now,
            )
            .order_by(AppointmentReminder.due_at.asc())
        )

        if dealership_id:
            query = query.filter(AppointmentReminder.dealership_id == dealership_id)

        reminders = query.all()

        scanned = len(reminders)
        sent = 0
        failed = 0

        for reminder in reminders:
            appointment = (
                self.db.query(Appointment)
                .filter(
                    Appointment.dealership_id == reminder.dealership_id,
                    Appointment.public_id == reminder.appointment_public_id,
                )
                .first()
            )

            if not appointment:
                reminder.status = "failed"
                failed += 1
                continue

            lead = self.leads.get_by_public_id(reminder.dealership_id, appointment.lead_id)
            if not lead or not getattr(lead, "email", None):
                reminder.status = "failed"
                failed += 1
                continue

            ok = self.email.send_appointment_reminder(lead, appointment, reminder.reminder_type)
            if ok:
                reminder.status = "sent"
                reminder.sent_at = now
                sent += 1
            else:
                reminder.status = "failed"
                failed += 1

        self.db.commit()

        result = {
            "scanned": scanned,
            "sent": sent,
            "failed": failed,
        }
        logger.info("Email reminder dispatch finished: %s", result)
        return result