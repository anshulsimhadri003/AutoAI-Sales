from __future__ import annotations

from statistics import mean

from sqlalchemy.orm import Session

from shared.models.models import Appointment, Lead
from shared.repositories.appointment_repository import AppointmentRepository
from shared.repositories.lead_repository import LeadRepository
from shared.repositories.sequence_repository import SequenceRepository


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.leads = LeadRepository(db)
        self.sequences = SequenceRepository(db)
        self.appointments = AppointmentRepository(db)

    def lead_metrics(self, dealership_id: str):
        rows = self.leads.list_all(dealership_id)
        hot = len([x for x in rows if x.temperature == "Hot"])
        active = len([x for x in rows if x.status in {"Open", "Working", "Escalated", "Appointment Scheduled"}])
        response_times = []
        for row in rows:
            if row.first_response_at and row.last_customer_message_at:
                response_times.append((row.first_response_at - row.last_customer_message_at).total_seconds() / 60)
        avg = f"{mean(response_times):.1f} min" if response_times else "N/A"
        return {
            "leads_processed": len(rows),
            "avg_response_time": avg,
            "hot_leads": hot,
            "active_conversations": active,
        }

    def sequence_metrics(self, dealership_id: str):
        rows = self.sequences.list_all(dealership_id)
        events = self.sequences.list_message_events(dealership_id)
        outbound = len([x for x in events if x.direction == "outbound"])
        inbound = len([x for x in events if x.direction == "inbound"])
        engagement_rate = f"{(inbound / outbound * 100):.0f}%" if outbound else "0%"
        response_rate = f"{(len([x for x in events if x.replied_at is not None]) / outbound * 100):.0f}%" if outbound else "0%"
        return {
            "active_sequences": len([x for x in rows if x.status == "Active"]),
            "engagement_rate": engagement_rate,
            "response_rate": response_rate,
            "escalations": len([x for x in rows if x.escalated]),
        }

    def appointment_metrics(self, dealership_id: str):
        rows = self.appointments.list_all(dealership_id)
        scheduled = len(rows)
        shows = len([x for x in rows if x.attendance_status == "show"])
        no_shows = len([x for x in rows if x.attendance_status == "no_show"])
        show_rate = f"{(shows / scheduled * 100):.0f}%" if scheduled else "0%"
        no_show_rate = f"{(no_shows / scheduled * 100):.0f}%" if scheduled else "0%"
        reschedules = len([x for x in rows if x.rescheduled_from_public_id])
        return {
            "appointments_scheduled": scheduled,
            "show_rate": show_rate,
            "no_show_rate": no_show_rate,
            "reschedules": reschedules,
        }
