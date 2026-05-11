from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from apps.api_gateway.services.sequence_engine import SequenceEngine
from shared.bootstrap.config_cache import get_config_cache
from shared.integrations.email_client import EmailClient
from shared.models.models import Appointment, Dealership, MessageEvent, Sequence
from shared.repositories.lead_repository import LeadRepository
from shared.repositories.sequence_repository import SequenceRepository

logger = logging.getLogger(__name__)


class NurtureDispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SequenceRepository(db)
        self.leads = LeadRepository(db)
        self.engine = SequenceEngine(db)
        self.email = EmailClient()
        self.config = get_config_cache()

    def run_due_sequences(self, dealership_id: str | None = None) -> dict:
        now = datetime.utcnow()

        query = (
            self.db.query(Sequence)
            .filter(
                Sequence.status == "Active",
                Sequence.next_run_at.is_not(None),
                Sequence.next_run_at <= now,
            )
            .order_by(Sequence.next_run_at.asc(), Sequence.id.asc())
        )

        if dealership_id:
            query = query.filter(Sequence.dealership_id == dealership_id)

        sequences = query.all()

        processed = 0
        sent = 0
        skipped = 0
        failed = 0

        for sequence in sequences:
            processed += 1

            lead = None
            if sequence.lead_public_id:
                lead = self.leads.get_by_public_id(sequence.dealership_id, sequence.lead_public_id)

            if not lead:
                sequence.status = "Escalated"
                sequence.escalated = True
                sequence.paused_reason = "Lead not found for nurture dispatch"
                self.repo.save(sequence)
                failed += 1
                continue

            channel = (sequence.channel or "Email").strip().lower()
            if channel != "email":
                skipped += 1
                sequence.next_run_at = now
                self.repo.save(sequence)
                continue

            step = self.engine._step_for_order(sequence.definition_public_id, sequence.current_step)
            if not step:
                sequence.status = "Completed"
                sequence.next_step = "Completed"
                sequence.current_template_id = None
                sequence.next_run_at = None
                self.repo.save(sequence)
                skipped += 1
                continue

            template = self.config.get_message_template(step.template_id)
            if not template:
                sequence.status = "Escalated"
                sequence.escalated = True
                sequence.paused_reason = f"Missing template for {step.template_id}"
                self.repo.save(sequence)
                failed += 1
                continue

            if not self._condition_matches(sequence, lead, step.condition_type, step.condition_value):
                sequence.next_run_at = now + self._minutes(step.delay_minutes)
                self.repo.save(sequence)
                skipped += 1
                continue

            dealership = (
                self.db.query(Dealership)
                .filter(Dealership.public_id == sequence.dealership_id)
                .first()
            )

            render_context = {
                "vehicle": lead.vehicle_interest or "the vehicle",
                "dealership_name": dealership.name if dealership else sequence.dealership_id,
                "appointment_time": "your preferred time",
            }

            body = self.config.render_template_text(template, **render_context)
            subject = self._build_subject(sequence, template, lead)

            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #1f2937;">
                <p>Hello {(lead.first_name or '').strip() or 'there'},</p>
                <p>{body}</p>
                <p>Thank you,<br/>Halcyon Auto Sales</p>
              </body>
            </html>
            """

            ok = self.email.send_nurture_email(
                to_email=lead.email,
                subject=subject,
                text_body=body,
                html_body=html_body,
            )

            if ok:
                lead.last_agent_message_at = now
                self.leads.save(lead)
                self.engine.register_outbound(
                    sequence,
                    lead,
                    body,
                    template.template_id,
                    "email",
                    classification="followup_sent",
                )
                sent += 1
            else:
                self.repo.create_message_event(
                    MessageEvent(
                        dealership_id=sequence.dealership_id,
                        sequence_public_id=sequence.public_id,
                        lead_public_id=lead.public_id,
                        channel="email",
                        direction="outbound",
                        template_key=template.template_id,
                        classification="followup_failed",
                        delivery_status="failed",
                        content=body,
                        created_at=now,
                    )
                )
                sequence.status = "Escalated"
                sequence.escalated = True
                sequence.paused_reason = "SMTP send failed"
                self.repo.save(sequence)
                failed += 1

        return {
            "processed": processed,
            "sent": sent,
            "skipped": skipped,
            "failed": failed,
        }

    def _condition_matches(self, sequence, lead, condition_type: str | None, condition_value: str | None) -> bool:
        condition_type = (condition_type or "always").strip().lower()
        condition_value = (condition_value or "").strip().lower()

        if condition_type == "always":
            return True

        if condition_type == "no_reply":
            return self._has_no_reply_since_last_outbound(lead.dealership_id, lead.public_id)

        if condition_type == "clicked_link":
            return self._has_any_click(lead.dealership_id, lead.public_id)

        if condition_type == "high_intent":
            return (
                lead.temperature == "Hot"
                or (lead.score or 0) >= 80
                or (lead.urgency or "").lower() in {"immediate", "high_intent", "high intent"}
            )

        if condition_type == "appointment_booked":
            return self._has_confirmed_appointment(lead.dealership_id, lead.public_id)

        if condition_type == "finance_question":
            return (sequence.last_message_classification or "").lower() == "finance_question"

        if condition_type == "manager_escalation":
            return bool(sequence.escalated)

        if condition_type == "vehicle_unavailable":
            return (lead.next_action or "").lower() == "recommend alternative vehicles"

        return False

    def _has_no_reply_since_last_outbound(self, dealership_id: str, lead_public_id: str) -> bool:
        events = self.repo.list_message_events_for_lead(dealership_id, lead_public_id)
        last_outbound = next((e for e in events if e.direction == "outbound"), None)
        if not last_outbound:
            return True
        return not any(
            e.direction == "inbound" and e.created_at and e.created_at > last_outbound.created_at
            for e in events
        )

    def _has_any_click(self, dealership_id: str, lead_public_id: str) -> bool:
        events = self.repo.list_message_events_for_lead(dealership_id, lead_public_id)
        return any(e.clicked_at is not None for e in events)

    def _has_confirmed_appointment(self, dealership_id: str, lead_public_id: str) -> bool:
        return (
            self.db.query(Appointment)
            .filter(
                Appointment.dealership_id == dealership_id,
                Appointment.lead_id == lead_public_id,
                Appointment.status.in_(["Confirmed", "Rescheduled"]),
            )
            .first()
            is not None
        )

    @staticmethod
    def _minutes(value: int):
        from datetime import timedelta
        return timedelta(minutes=max(value, 15))

    @staticmethod
    def _build_subject(sequence, template, lead) -> str:
        lead_name = " ".join(part for part in [lead.first_name, lead.last_name] if part).strip()
        if template.template_type == "reminder":
            return f"Halcyon Auto: Reminder for {lead_name or lead.public_id}"
        if template.intent_tag == "test_drive":
            return f"Halcyon Auto: Schedule your test drive"
        if template.intent_tag == "finance":
            return f"Halcyon Auto: Finance options for your vehicle"
        if template.intent_tag == "availability":
            return f"Halcyon Auto: Availability update"
        return f"Halcyon Auto: Follow-up for {lead_name or lead.public_id}"