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
        converted = len([x for x in rows if x.status in {"Appointment Scheduled", "Showed"}])
        sla_breached = len([x for x in rows if x.escalated_at is not None or x.status == "Escalated"])
        pending_response = len([x for x in rows if x.first_response_at is None and x.status in {"Open", "Working", "Escalated"}])
        conversion_rate = f"{(converted / len(rows) * 100):.0f}%" if rows else "0%"
        return {
            "leads_processed": len(rows),
            "avg_response_time": avg,
            "hot_leads": hot,
            "active_conversations": active,
            "conversion_rate": conversion_rate,
            "sla_breached": sla_breached,
            "pending_response": pending_response,
        }

    def sequence_metrics(self, dealership_id: str):
        rows = self.sequences.list_all(dealership_id)
        events = self.sequences.list_message_events(dealership_id)
        outbound = len([x for x in events if x.direction == "outbound"])
        inbound = len([x for x in events if x.direction == "inbound"])
        engagement_rate = f"{(inbound / outbound * 100):.0f}%" if outbound else "0%"
        response_rate = f"{(len([x for x in events if x.replied_at is not None]) / outbound * 100):.0f}%" if outbound else "0%"
        opened = len([x for x in events if x.opened_at is not None])
        clicked = len([x for x in events if x.clicked_at is not None])
        return {
            "active_sequences": len([x for x in rows if x.status == "Active"]),
            "engagement_rate": engagement_rate,
            "response_rate": response_rate,
            "escalations": len([x for x in rows if x.escalated]),
            "messages_sent": outbound,
            "opens": opened,
            "clicks": clicked,
            "replies": inbound,
        }

    def appointment_metrics(self, dealership_id: str):
        rows = self.appointments.list_all(dealership_id)
        scheduled = len(rows)
        shows = len([x for x in rows if x.attendance_status == "show"])
        no_shows = len([x for x in rows if x.attendance_status == "no_show"])
        show_rate = f"{(shows / scheduled * 100):.0f}%" if scheduled else "0%"
        no_show_rate = f"{(no_shows / scheduled * 100):.0f}%" if scheduled else "0%"
        reschedules = len([x for x in rows if x.rescheduled_from_public_id])
        confirmed = len([x for x in rows if x.status == "Confirmed"])
        return {
            "appointments_scheduled": scheduled,
            "show_rate": show_rate,
            "no_show_rate": no_show_rate,
            "reschedules": reschedules,
            "confirmed": confirmed,
            "shows": shows,
            "no_shows": no_shows,
        }

    def overview(self, dealership_id: str):
        leads = self.leads.list_all(dealership_id)
        sequences = self.sequences.list_all(dealership_id)
        appointments = self.appointments.list_all(dealership_id)
        by_temperature = {label: len([x for x in leads if x.temperature == label]) for label in ["Hot", "Warm", "Cold"]}
        by_status = {}
        for lead in leads:
            by_status[lead.status] = by_status.get(lead.status, 0) + 1
        by_channel = {}
        for lead in leads:
            by_channel[lead.source_channel] = by_channel.get(lead.source_channel, 0) + 1
        top_leads = sorted(leads, key=lambda row: row.score, reverse=True)[:8]
        return {
            "lead_metrics": self.lead_metrics(dealership_id),
            "sequence_metrics": self.sequence_metrics(dealership_id),
            "appointment_metrics": self.appointment_metrics(dealership_id),
            "charts": {
                "temperature": [{"name": key, "value": value} for key, value in by_temperature.items()],
                "lead_status": [{"name": key, "value": value} for key, value in by_status.items()],
                "lead_channels": [{"name": key, "value": value} for key, value in by_channel.items()],
            },
            "top_leads": [
                {
                    "public_id": lead.public_id,
                    "name": f"{lead.first_name} {lead.last_name}".strip(),
                    "score": lead.score,
                    "temperature": lead.temperature,
                    "urgency": lead.urgency,
                    "vehicle_interest": lead.vehicle_interest,
                    "assigned_rep": lead.assigned_rep,
                    "status": lead.status,
                }
                for lead in top_leads
            ],
            "qa_progress": [
                {"agent": "AI Lead Qualification & Routing", "status": "Partial Complete", "priority": "High"},
                {"agent": "Follow-Up & Nurture", "status": "Backend Partial", "priority": "High"},
                {"agent": "Appointment Scheduling", "status": "Backend Partial", "priority": "High"},
                {"agent": "React Frontend", "status": "Added", "priority": "High"},
            ],
        }

