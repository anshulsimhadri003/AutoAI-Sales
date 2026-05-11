from __future__ import annotations

import logging
from datetime import datetime

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from apps.api_gateway.graphs.orchestrator import run_booking_graph, run_reschedule_graph
from apps.api_gateway.services.reminder_service import ReminderService
from shared.integrations.calendar_client import CalendarClient
from shared.integrations.email_client import EmailClient
from shared.integrations.inventory_client import InventoryClient
from shared.models.models import Appointment
from shared.repositories.appointment_repository import AppointmentRepository
from shared.repositories.lead_repository import LeadRepository
from shared.schemas.appointments import AppointmentBookRequest, AppointmentRescheduleRequest

logger = logging.getLogger(__name__)


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AppointmentRepository(db)
        self.leads = LeadRepository(db)
        self.inventory = InventoryClient(db)
        self.calendar = CalendarClient(db)
        self.email = EmailClient()
        self.reminders = ReminderService(db)

    def list_appointments(self, dealership_id: str):
        return self.repo.list_all(dealership_id)

    def get_slots(self, dealership_id: str, vehicle_id: str, date: str):
        state = self.inventory.get_vehicle_state(dealership_id, vehicle_id)
        if not state["test_drive_available"]:
            return []
        return self.calendar.get_available_slots(dealership_id, vehicle_id, date)

    def book_appointment(self, dealership_id: str, payload: AppointmentBookRequest, background_tasks: BackgroundTasks | None = None):
        return run_booking_graph(self, dealership_id, payload, background_tasks)

    def reschedule_appointment(self, dealership_id: str, payload: AppointmentRescheduleRequest, background_tasks: BackgroundTasks | None = None):
        return run_reschedule_graph(self, dealership_id, payload, background_tasks)

    def _validate_booking_request(self, dealership_id: str, payload: AppointmentBookRequest) -> dict:
        state = self.inventory.get_vehicle_state(dealership_id, payload.vehicle_id)
        if not state["test_drive_available"]:
            raise ValueError(self._alternative_vehicle_message(dealership_id, payload.vehicle_id, suffix="appointment alternative"))
        if not self.calendar.is_slot_available(dealership_id, payload.vehicle_id, payload.rep_id, payload.start_time, payload.end_time):
            raise ValueError("Requested slot is no longer available for that rep. Please choose another slot.")
        return {"vehicle_state": state}

    def _persist_booking(self, state: dict, background_tasks: BackgroundTasks | None = None):
        payload: AppointmentBookRequest = state["payload"]
        validation = state["validation"]
        appointment = Appointment(
            dealership_id=state["dealership_id"],
            public_id=self.repo.next_public_id(state["dealership_id"]),
            lead_id=payload.lead_id,
            vehicle_id=payload.vehicle_id,
            rep_id=payload.rep_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            channel=payload.channel,
            status="Confirmed",
            vehicle_location=validation["vehicle_state"]["location"],
            vehicle_status=validation["vehicle_state"]["status"],
            attendance_status="scheduled",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        created = self.repo.create(appointment)
        self.calendar.create_event(state["dealership_id"], created)
        self.reminders.schedule_for_appointment(created)
        lead = self.leads.get_by_public_id(state["dealership_id"], payload.lead_id)
        if lead:
            lead.status = "Appointment Scheduled"
            if lead.first_response_at is None:
                lead.first_response_at = datetime.utcnow()
            lead.last_agent_message_at = datetime.utcnow()
            self.leads.save(lead)
            if background_tasks:
                background_tasks.add_task(self.email.send_appointment_confirmation, lead, created)
            else:
                self.email.send_appointment_confirmation(lead, created)
        else:
            logger.warning(
                "Appointment %s was created but no lead was found for %s, so no email was sent.",
                created.public_id,
                payload.lead_id,
            )
        return created

    def _validate_reschedule_request(self, dealership_id: str, payload: AppointmentRescheduleRequest) -> dict:
        existing = self.repo.get_by_public_id(dealership_id, payload.appointment_id)
        if not existing:
            raise ValueError("Appointment not found")
        vehicle_id = payload.new_vehicle_id or existing.vehicle_id
        state = self.inventory.get_vehicle_state(dealership_id, vehicle_id)
        if not state["test_drive_available"]:
            raise ValueError(self._alternative_vehicle_message(dealership_id, vehicle_id, suffix="reschedule alternative"))
        if not self.calendar.is_slot_available(dealership_id, vehicle_id, existing.rep_id, payload.start_time, payload.end_time):
            raise ValueError("Requested reschedule slot is no longer available for that rep.")
        return {"existing": existing, "vehicle_id": vehicle_id, "vehicle_state": state}

    def _persist_reschedule(self, state: dict, background_tasks: BackgroundTasks | None = None):
        payload: AppointmentRescheduleRequest = state["payload"]
        validation = state["validation"]
        existing = validation["existing"]
        existing.status = "Rescheduled"
        self.repo.save(existing)
        new_appointment = Appointment(
            dealership_id=state["dealership_id"],
            public_id=self.repo.next_public_id(state["dealership_id"]),
            lead_id=existing.lead_id,
            vehicle_id=validation["vehicle_id"],
            rep_id=existing.rep_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            channel=existing.channel,
            status="Confirmed",
            vehicle_location=validation["vehicle_state"]["location"],
            vehicle_status=validation["vehicle_state"]["status"],
            attendance_status="scheduled",
            rescheduled_from_public_id=existing.public_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        created = self.repo.create(new_appointment)
        self.reminders.schedule_for_appointment(created)
        lead = self.leads.get_by_public_id(state["dealership_id"], created.lead_id)
        if lead:
            if background_tasks:
                background_tasks.add_task(self.email.send_appointment_confirmation, lead, created)
            else:
                self.email.send_appointment_confirmation(lead, created)
        return created

    def _alternative_vehicle_message(self, dealership_id: str, vehicle_id: str, *, suffix: str) -> str:
        query_vehicle = vehicle_id
        state = self.inventory.get_vehicle_state(dealership_id, vehicle_id)
        if state.get("vehicle") is not None:
            vehicle = state["vehicle"]
            query_vehicle = f"{vehicle.year} {vehicle.make_model} {vehicle.trim} {vehicle.body_type} {vehicle.fuel_type} {vehicle.transmission}"
        alternatives = self.inventory.recommend_alternatives(
            dealership_id,
            query_text=f"{query_vehicle} {suffix}",
            exclude_vehicle_id=vehicle_id,
            top_k=3,
        )
        names = ", ".join(vehicle.make_model for vehicle in alternatives) or "no close alternatives right now"
        return f"Vehicle is no longer available. Suggested alternatives: {names}"

    def mark_attendance(self, dealership_id: str, appointment_id: str, attendance_status: str):
        appointment = self.repo.get_by_public_id(dealership_id, appointment_id)
        if not appointment:
            return None
        if attendance_status not in {"show", "no_show"}:
            raise ValueError("attendance_status must be show or no_show")
        appointment.attendance_status = attendance_status
        appointment.status = "Completed" if attendance_status == "show" else "No Show"
        saved = self.repo.save(appointment)
        lead = self.leads.get_by_public_id(dealership_id, appointment.lead_id)
        if lead:
            lead.status = "Showed" if attendance_status == "show" else "No Show"
            self.leads.save(lead)
        return saved

