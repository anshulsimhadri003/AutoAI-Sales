from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from apps.api_gateway.graphs.orchestrator import run_reply_graph
from apps.api_gateway.services.semantic_service import get_semantic_service
from apps.api_gateway.services.sequence_engine import SequenceEngine
from shared.integrations.openai_client import OpenAIClient
from shared.models.models import Dealership
from shared.repositories.lead_repository import LeadRepository
from shared.repositories.sequence_repository import SequenceRepository
from shared.schemas.messages import AIReplyRequest, AIReplyResponse


class NurtureService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SequenceRepository(db)
        self.leads = LeadRepository(db)
        self.semantic = get_semantic_service()
        self.openai = OpenAIClient()
        self.engine = SequenceEngine(db)

    def list_sequences(self, dealership_id: str):
        return self.repo.list_all(dealership_id)

    def generate_reply(self, dealership_id: str, payload: AIReplyRequest) -> AIReplyResponse:
        return run_reply_graph(self, dealership_id, payload)

    def _load_reply_context(self, dealership_id: str, payload: AIReplyRequest) -> dict:
        lead = self.leads.get_by_public_id(dealership_id, payload.lead_id) if payload.lead_id else None
        sequence = self.repo.get_active_for_lead(dealership_id, payload.lead_id) if payload.lead_id else None
        dealership = self.db.query(Dealership).filter(Dealership.public_id == dealership_id).first()
        return {
            "normalized_message": (payload.message or "").strip(),
            "lead": lead,
            "sequence": sequence,
            "dealership": dealership,
            "render_context": {
                "vehicle": lead.vehicle_interest if lead else "the vehicle",
                "dealership_name": dealership.name if dealership else dealership_id,
                "appointment_time": "your preferred time",
            },
        }

    def _classify_reply_context(self, state: dict) -> dict:
        context = state["context"]
        lead = context["lead"]
        message = context["normalized_message"]
        canonical_message = message.lower().rstrip("?.! ")
        if canonical_message in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
            intent_label, intent_score = "greeting", 1.0
            urgency_label, urgency_score = "Research Phase", 0.6
            message_type, message_type_score = "greeting", 1.0
        elif canonical_message in {"what can you do", "how can you help", "how can you help me", "what services do you provide", "what do you do", "who are you", "help"}:
            intent_label, intent_score = "capability", 1.0
            urgency_label, urgency_score = "Research Phase", 0.6
            message_type, message_type_score = "capability", 1.0
        elif canonical_message in {"thanks", "thank you", "appreciate it"}:
            intent_label, intent_score = "general_help", 0.8
            urgency_label, urgency_score = "Research Phase", 0.6
            message_type, message_type_score = "thanks", 1.0
        else:
            intent_label, intent_score = self.semantic.classify_intent(message, lead.vehicle_interest if lead else "")
            urgency_label, urgency_score = self.semantic.classify_urgency(message)
            message_type, message_type_score = self.semantic.classify_message_type(message)
        resolved_intent = lead.semantic_intent if lead and lead.semantic_intent else intent_label
        resolved_urgency = lead.urgency if lead and lead.urgency else urgency_label
        resolved_channel = (context["sequence"].channel if context["sequence"] else "email").lower()
        if resolved_channel not in {"email", "sms", "whatsapp", "any"}:
            resolved_channel = "email"
        if not lead and intent_score < 0.38 and message_type not in {"greeting", "thanks", "capability"}:
            resolved_intent = "general_help"
        return {
            "intent_label": resolved_intent,
            "intent_score": intent_score,
            "urgency_label": resolved_urgency,
            "urgency_score": urgency_score,
            "message_type": message_type,
            "message_type_score": message_type_score,
            "resolved_channel": resolved_channel,
        }

    def _retrieve_reply_materials(self, state: dict) -> dict:
        context = state["context"]
        classification = state["classification"]
        message = context["normalized_message"]
        lead = context["lead"]
        sequence = context["sequence"]
        knowledge = self.semantic.retrieve_knowledge(message, top_k=3, intent_tag=classification["intent_label"])
        candidates = self.semantic.retrieve_reply_templates(
            message,
            top_k=3,
            intent_tag=classification["intent_label"],
            urgency_tag=classification["urgency_label"],
            channel=classification["resolved_channel"],
            preferred_template_id=sequence.current_template_id if sequence else None,
            render_context=context["render_context"],
            template_type="reply",
        )
        if not candidates and knowledge:
            candidates = [{"key": item["knowledge_id"], "text": item["text"]} for item in knowledge[:3]]
        return {"knowledge": knowledge, "candidates": candidates, "lead_present": lead is not None}

    def _compose_reply_from_state(self, state: dict) -> str:
        context = state["context"]
        classification = state["classification"]
        retrieval = state["retrieval"]
        payload: AIReplyRequest = state["payload"]
        reply_context = {
            "lead_id": payload.lead_id or "unknown",
            "dealership_id": state["dealership_id"],
            "intent_label": classification["intent_label"],
            "intent_score": classification["intent_score"],
            "urgency_label": classification["urgency_label"],
            "urgency_score": classification["urgency_score"],
            "message_type": classification["message_type"],
            "message_type_score": classification["message_type_score"],
            "candidate_replies": [item["text"] for item in retrieval["candidates"]],
            "knowledge_snippets": [item["text"] for item in retrieval["knowledge"]],
            "customer_message": context["normalized_message"],
        }
        return self.openai.grounded_reply(reply_context)

    def _persist_reply_from_state(self, state: dict) -> AIReplyResponse:
        context = state["context"]
        classification = state["classification"]
        retrieval = state["retrieval"]
        lead = context["lead"]
        sequence = context["sequence"]
        reply = state["reply"]
        if lead:
            lead.last_customer_message_at = datetime.utcnow()
            self.leads.save(lead)
            self.engine.register_inbound(sequence, lead, context["normalized_message"])
            if lead.first_response_at is None:
                lead.first_response_at = datetime.utcnow()
            lead.last_agent_message_at = datetime.utcnow()
            if classification["message_type"] not in {"opt_out", "complex_question"}:
                lead.status = "Working"
            self.leads.save(lead)
            self.engine.register_outbound(
                sequence,
                lead,
                reply,
                retrieval["candidates"][0]["key"] if retrieval["candidates"] else None,
                classification["resolved_channel"],
            )
        return AIReplyResponse(reply=reply)
