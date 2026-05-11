from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from apps.api_gateway.services.semantic_service import get_semantic_service
from shared.bootstrap.config_cache import get_config_cache
from shared.models.models import Lead, MessageEvent, Sequence, SequenceDefinition, SequenceStepDefinition
from shared.repositories.sequence_repository import SequenceRepository


class SequenceEngine:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SequenceRepository(db)
        self.semantic = get_semantic_service()
        self.config = get_config_cache()

    def ensure_sequence_for_lead(self, lead: Lead) -> Sequence:
        existing = self.repo.get_active_for_lead(lead.dealership_id, lead.public_id)
        if existing:
            return existing

        definition = self._select_sequence_definition(lead)
        steps = self._steps_for_definition(definition.public_id if definition else None)
        first_step = steps[0] if steps else None
        cadence = first_step.delay_minutes if first_step else self._default_cadence(lead)
        sequence = Sequence(
            dealership_id=lead.dealership_id,
            public_id=self.repo.next_public_id(lead.dealership_id),
            name=definition.name if definition else self._sequence_name(lead),
            lead_name=f"{lead.first_name} {lead.last_name}".strip(),
            lead_public_id=lead.public_id,
            definition_public_id=definition.public_id if definition else None,
            channel=self._channel_label(definition.channel if definition else self._preferred_channel(lead.source_channel)),
            engagement=self._engagement_from_signals(lead),
            status="Active",
            next_step=self._step_label(first_step, fallback=lead.next_action),
            current_step=1,
            total_steps=max(len(steps), 1),
            cadence_minutes=cadence,
            current_template_id=first_step.template_id if first_step else None,
            next_run_at=datetime.utcnow() + timedelta(minutes=cadence),
        )
        return self.repo.create(sequence)

    def register_inbound(self, sequence: Sequence | None, lead: Lead, message: str) -> str:
        classification, _ = self.semantic.classify_message_type(message)
        self.repo.create_message_event(
            MessageEvent(
                dealership_id=lead.dealership_id,
                sequence_public_id=sequence.public_id if sequence else None,
                lead_public_id=lead.public_id,
                channel=sequence.channel if sequence else lead.source_channel,
                direction="inbound",
                classification=classification,
                delivery_status="received",
                replied_at=datetime.utcnow(),
                content=message,
                created_at=datetime.utcnow(),
            )
        )
        if sequence:
            sequence.last_message_classification = classification
            if classification == "opt_out":
                sequence.status = "Paused"
                sequence.paused_reason = "Customer opted out"
            elif classification in {"schedule_interest", "finance_question", "inventory_question"}:
                sequence.status = "Paused"
                sequence.paused_reason = "Awaiting sales rep action"
            elif classification == "complex_question":
                sequence.status = "Escalated"
                sequence.escalated = True
                sequence.paused_reason = "Complex question requires human follow-up"
            elif classification == "objection":
                sequence.cadence_minutes = min(sequence.cadence_minutes * 2, 4320)
                sequence.next_run_at = datetime.utcnow() + timedelta(minutes=sequence.cadence_minutes)
                sequence.next_step = "Handle objection"
            else:
                sequence.next_run_at = datetime.utcnow() + timedelta(minutes=sequence.cadence_minutes)
            sequence.engagement = self._engagement_from_events(lead.dealership_id, lead.public_id)
            self.db.commit()
            self.db.refresh(sequence)
        return classification

    def register_outbound(
        self,
        sequence: Sequence | None,
        lead: Lead,
        content: str,
        template_key: str | None,
        channel: str,
        classification: str = "reply_sent",
    ):
        template_key = template_key or (sequence.current_template_id if sequence else None)
        self.repo.create_message_event(
            MessageEvent(
                dealership_id=lead.dealership_id,
                sequence_public_id=sequence.public_id if sequence else None,
                lead_public_id=lead.public_id,
                channel=channel,
                direction="outbound",
                template_key=template_key,
                classification=classification,
                delivery_status="sent",
                content=content,
                created_at=datetime.utcnow(),
            )
        )
        if sequence:
            next_step = self._step_for_order(sequence.definition_public_id, sequence.current_step + 1)
            if next_step:
                sequence.current_step = min(sequence.current_step + 1, sequence.total_steps)
                sequence.current_template_id = next_step.template_id
                sequence.cadence_minutes = next_step.delay_minutes
                sequence.next_step = self._step_label(next_step, fallback=sequence.next_step)
                sequence.next_run_at = datetime.utcnow() + timedelta(minutes=next_step.delay_minutes)
            else:
                sequence.status = "Completed"
                sequence.current_template_id = None
                sequence.next_step = "Completed"
                sequence.next_run_at = None
            sequence.engagement = self._engagement_from_events(lead.dealership_id, lead.public_id)
            self.db.commit()
            self.db.refresh(sequence)

    def _sequence_name(self, lead: Lead) -> str:
        if lead.temperature == "Hot":
            return "Hot Lead Fast Track"
        if lead.temperature == "Warm":
            return "Warm Lead Nurture"
        return "Cold Lead Re-Engage"

    def _preferred_channel(self, source_channel: str) -> str:
        if source_channel.lower() in {"whatsapp", "sms", "email"}:
            return source_channel.lower()
        return "email"

    def _channel_label(self, channel: str) -> str:
        normalized = (channel or "email").lower()
        if normalized == "sms":
            return "SMS"
        if normalized == "whatsapp":
            return "WhatsApp"
        return "Email"

    def _engagement_from_signals(self, lead: Lead) -> str:
        intensity = lead.page_views + lead.chat_interactions + lead.financing_inquiries + lead.trade_in_requests
        if lead.test_drive_interest or intensity >= 10:
            return "High"
        if intensity >= 4:
            return "Medium"
        return "Low"

    def _engagement_from_events(self, dealership_id: str, lead_public_id: str) -> str:
        rows = self.repo.list_message_events_for_lead(dealership_id, lead_public_id)
        outbound = len([row for row in rows if row.direction == "outbound"])
        inbound = len([row for row in rows if row.direction == "inbound"])
        if inbound >= 2 or (outbound and inbound / max(outbound, 1) >= 0.6):
            return "High"
        if inbound >= 1:
            return "Medium"
        return "Low"

    def _select_sequence_definition(self, lead: Lead) -> SequenceDefinition | None:
        trigger_type = {"Hot": "hot_lead", "Warm": "warm_lead", "Cold": "cold_lead"}.get(lead.temperature, "warm_lead")
        preferred_channel = self._preferred_channel(lead.source_channel)
        rows = (
            self.db.query(SequenceDefinition)
            .filter(
                SequenceDefinition.is_active.is_(True),
                SequenceDefinition.trigger_type == trigger_type,
            )
            .order_by(SequenceDefinition.public_id.asc())
            .all()
        )
        if not rows:
            return None
        exact = next((row for row in rows if row.channel.lower() == preferred_channel), None)
        return exact or rows[0]

    def _steps_for_definition(self, definition_public_id: str | None) -> list[SequenceStepDefinition]:
        if not definition_public_id:
            return []
        return (
            self.db.query(SequenceStepDefinition)
            .filter(SequenceStepDefinition.sequence_public_id == definition_public_id)
            .order_by(SequenceStepDefinition.step_order.asc())
            .all()
        )

    def _step_for_order(self, definition_public_id: str | None, step_order: int) -> SequenceStepDefinition | None:
        if not definition_public_id:
            return None
        return (
            self.db.query(SequenceStepDefinition)
            .filter(
                SequenceStepDefinition.sequence_public_id == definition_public_id,
                SequenceStepDefinition.step_order == step_order,
            )
            .first()
        )

    def _step_label(self, step: SequenceStepDefinition | None, fallback: str) -> str:
        if step is None:
            return fallback
        template = self.config.get_message_template(step.template_id)
        if template:
            template_type = template.template_type.replace("_", " ").title()
            intent = template.intent_tag.replace("_", " ").title() if template.intent_tag else template.channel.upper()
            return f"{template_type}: {intent}"
        return step.template_id or fallback

    def _default_cadence(self, lead: Lead) -> int:
        if lead.temperature == "Hot":
            return 180
        if lead.temperature == "Warm":
            return 720
        return 1440
