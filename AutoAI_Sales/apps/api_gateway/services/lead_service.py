from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from apps.api_gateway.graphs.orchestrator import run_lead_intake
from apps.api_gateway.services.routing_service import RoutingService
from apps.api_gateway.services.semantic_service import get_semantic_service
from apps.api_gateway.services.sequence_engine import SequenceEngine
from shared.config.settings import get_settings
from shared.integrations.crm_client import CRMClient
from shared.models.models import DealershipRule, Lead, UserEvent
from shared.repositories.lead_repository import LeadRepository
from shared.repositories.user_event_repository import UserEventRepository
from shared.schemas.lead_events import ExternalLeadCreateData, LeadEventRequest, LeadEventResponse, LeadSnapshotResponse
from shared.schemas.leads import LeadCreateRequest, LeadIntentSignals


class LeadService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.repo = LeadRepository(db)
        self.user_events = UserEventRepository(db)
        self.semantic = get_semantic_service()
        self.crm = CRMClient()
        self.routing = RoutingService(db)
        self.sequences = SequenceEngine(db)

    def list_leads(self, dealership_id: str):
        self._run_response_time_monitor(dealership_id)
        return self.repo.list_all(dealership_id)

    def get_lead(self, dealership_id: str, lead_id: str):
        self._run_response_time_monitor(dealership_id)
        return self.repo.get_by_public_id(dealership_id, lead_id)

    def create_lead(self, dealership_id: str, payload: LeadCreateRequest):
        return run_lead_intake(self, dealership_id, payload)

    def handle_lead_event(self, dealership_id: str, payload: LeadEventRequest) -> LeadEventResponse:
        if payload.action == "CREATE_LEAD":
            return self._handle_create_lead_event(dealership_id, payload)
        return self._handle_track_event(dealership_id, payload)

    def _handle_create_lead_event(self, dealership_id: str, payload: LeadEventRequest) -> LeadEventResponse:
        create_data = ExternalLeadCreateData.model_validate(payload.data)
        lead_request = self._build_lead_request_from_external(create_data)
        lead = self.create_lead(dealership_id, lead_request)
        lead = self._enrich_lead_with_external_payload(lead, payload.sessionId, create_data)
        event = self._store_user_event(
            dealership_id=dealership_id,
            session_id=payload.sessionId,
            action=payload.action,
            event_type=None,
            lead_public_id=lead.public_id,
            data=create_data.model_dump(),
        )
        return LeadEventResponse(
            action=payload.action,
            sessionId=payload.sessionId,
            eventType=None,
            userEventId=event.public_id,
            leadPublicId=lead.public_id,
            status="processed",
            detail="Lead created and session linked successfully.",
            processedAt=event.created_at,
            lead=self._lead_snapshot(lead),
        )

    def _handle_track_event(self, dealership_id: str, payload: LeadEventRequest) -> LeadEventResponse:
        lead = self._resolve_lead_for_session(dealership_id, payload.sessionId)
        event = self._store_user_event(
            dealership_id=dealership_id,
            session_id=payload.sessionId,
            action=payload.action,
            event_type=payload.eventType,
            lead_public_id=lead.public_id if lead else None,
            data=payload.data,
        )
        if lead is None:
            return LeadEventResponse(
                action=payload.action,
                sessionId=payload.sessionId,
                eventType=payload.eventType,
                userEventId=event.public_id,
                leadPublicId=None,
                status="accepted",
                detail="Event stored, but no lead is currently linked to this sessionId.",
                processedAt=event.created_at,
                lead=None,
            )

        updated_lead = self._apply_event_to_lead(lead, payload.eventType or "", payload.data)
        return LeadEventResponse(
            action=payload.action,
            sessionId=payload.sessionId,
            eventType=payload.eventType,
            userEventId=event.public_id,
            leadPublicId=updated_lead.public_id,
            status="processed",
            detail=f"{payload.eventType} tracked and lead score refreshed.",
            processedAt=event.created_at,
            lead=self._lead_snapshot(updated_lead),
        )

    def _build_lead_request_from_external(self, data: ExternalLeadCreateData) -> LeadCreateRequest:
        first_name, last_name = self._split_name(data.Name)
        inferred_vehicle_interest = (
            data.VehicleName
            or " ".join(part for part in [data.Year, data.Make, data.Model] if part).strip()
            or "Unknown Vehicle"
        )
        return LeadCreateRequest(
            source_channel="chatbot",
            first_name=first_name,
            last_name=last_name,
            email=data.Email,
            phone=data.PhoneNumber,
            vehicle_interest=inferred_vehicle_interest,
            message=data.Message or "Lead captured from chatbot",
            customer_location=data.Address or None,
        )

    def _enrich_lead_with_external_payload(self, lead: Lead, session_id: str, data: ExternalLeadCreateData) -> Lead:
        lead.session_id = session_id
        lead.external_vehicle_id = str(data.VehicleId) if data.VehicleId is not None else lead.external_vehicle_id
        lead.external_vehicle_name = data.VehicleName or lead.external_vehicle_name
        lead.vin = data.Vin or lead.vin
        lead.vehicle_year = data.Year or lead.vehicle_year
        lead.vehicle_make = data.Make or lead.vehicle_make
        lead.vehicle_model = data.Model or lead.vehicle_model
        if data.Address:
            lead.customer_location = data.Address
        if data.Message:
            lead.message = data.Message
        if not lead.engagement_history:
            lead.engagement_history = []
        lead.engagement_history.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "type": "CREATE_LEAD",
                "session_id": session_id,
                "vehicle": data.VehicleName,
            }
        )
        return self.repo.save(lead)

    def _resolve_lead_for_session(self, dealership_id: str, session_id: str) -> Lead | None:
        by_session = self.repo.get_by_session_id(dealership_id, session_id)
        if by_session:
            return by_session
        latest_event = self.user_events.get_latest_with_lead(dealership_id, session_id)
        if latest_event and latest_event.lead_public_id:
            return self.repo.get_by_public_id(dealership_id, latest_event.lead_public_id)
        return None

    def _store_user_event(
        self,
        *,
        dealership_id: str,
        session_id: str,
        action: str,
        event_type: str | None,
        lead_public_id: str | None,
        data: dict[str, Any],
    ) -> UserEvent:
        event = UserEvent(
            public_id=self.user_events.next_public_id(),
            dealership_id=dealership_id,
            session_id=session_id,
            lead_public_id=lead_public_id,
            action=action,
            event_type=event_type,
            payload=data,
            created_at=datetime.utcnow(),
        )
        return self.user_events.create(event)

    def _apply_event_to_lead(self, lead: Lead, event_type: str, data: dict[str, Any]) -> Lead:
        now = datetime.utcnow()
        message = self._extract_event_message(data)
        if message:
            lead.message = message
            lead.last_customer_message_at = now
        lead.status = "Working" if lead.status in {"Open", "Escalated"} else lead.status
        lead.previous_dealership_interactions = (lead.previous_dealership_interactions or 0) + 1

        if event_type in {"CHATBOT_AUTO_OPEN", "CHATBOT_CONVERSATION", "CHATBOT_LEAD", "CHATBOT_LEAD_SUBMITTED"}:
            lead.chat_interactions += 1
        if event_type in {"FILTER_APPLIED", "INVENTORY_FILTER_APPLIED", "SEARCH", "SCROLL_DEPTH", "VEHICLE_CLICK"}:
            lead.page_views += 1
        if event_type == "INVENTORY_DWELL_TIME":
            lead.vehicle_page_time_seconds += self._extract_dwell_time_seconds(data)
        if event_type == "VEHICLE_CLICK":
            vehicle_name = self._extract_vehicle_name(data)
            if vehicle_name:
                lead.vehicle_interest = vehicle_name
                lead.external_vehicle_name = vehicle_name
        if event_type == "CHATBOT_LEAD_SUBMITTED":
            lead.test_drive_interest = lead.test_drive_interest or self._event_implies_test_drive(data)

        if data.get("VehicleId") is not None:
            lead.external_vehicle_id = str(data["VehicleId"])
        if data.get("Vin"):
            lead.vin = str(data["Vin"])
        if data.get("Year"):
            lead.vehicle_year = str(data["Year"])
        if data.get("Make"):
            lead.vehicle_make = str(data["Make"])
        if data.get("Model"):
            lead.vehicle_model = str(data["Model"])
        if data.get("Address"):
            lead.customer_location = str(data["Address"])

        normalized_signals = self._normalize_signals(lead.intent_signals_model, message.lower() if message else "")
        lead.page_views = normalized_signals.page_views
        lead.vehicle_page_time_seconds = normalized_signals.vehicle_page_time_seconds
        lead.chat_interactions = normalized_signals.chat_interactions
        lead.financing_inquiries = normalized_signals.financing_inquiries
        lead.trade_in_requests = normalized_signals.trade_in_requests
        lead.test_drive_interest = normalized_signals.test_drive_interest

        semantic_intent, intent_similarity = self.semantic.classify_intent(lead.message, lead.vehicle_interest)
        urgency, urgency_similarity = self.semantic.classify_urgency(lead.message)
        lead.semantic_intent = semantic_intent
        lead.semantic_intent_similarity = max(intent_similarity, lead.semantic_intent_similarity or 0.0)
        lead.urgency = urgency if urgency_similarity >= 0.35 else lead.urgency
        lead.score = self._compute_score(normalized_signals, lead.semantic_intent_similarity, lead.urgency)
        lead.temperature = "Hot" if lead.score >= 80 else "Warm" if lead.score >= 50 else "Cold"
        lead.next_action, _ = self.semantic.choose_next_action(
            lead.message,
            lead.vehicle_interest,
            lead.temperature,
            inventory_available=True,
            intent_label=lead.semantic_intent,
            urgency_label=lead.urgency,
        )

        if not lead.assigned_rep_id:
            rep = self.routing.assign_rep(
                lead.dealership_id,
                message=lead.message,
                vehicle_interest=lead.vehicle_interest,
                location=lead.customer_location,
                score=lead.score,
                reserve=True,
            )
            if rep:
                lead.assigned_rep = rep.name
                lead.assigned_rep_id = rep.public_id

        if not lead.engagement_history:
            lead.engagement_history = []
        lead.engagement_history.append({"ts": now.isoformat(), "type": event_type, "payload": data})
        lead.updated_at = now
        saved = self.repo.save(lead)
        self.crm.upsert_lead(saved)
        self.sequences.ensure_sequence_for_lead(saved)
        return saved

    def _lead_snapshot(self, lead: Lead) -> LeadSnapshotResponse:
        return LeadSnapshotResponse(
            public_id=lead.public_id,
            session_id=lead.session_id,
            full_name=" ".join(part for part in [lead.first_name, lead.last_name] if part).strip(),
            email=lead.email,
            phone=lead.phone,
            vehicle_interest=lead.vehicle_interest,
            score=lead.score,
            temperature=lead.temperature,
            urgency=lead.urgency,
            assigned_rep=lead.assigned_rep,
            status=lead.status,
            intent_signals=lead.intent_signals_model,
        )

    @staticmethod
    def _split_name(name: str) -> tuple[str, str]:
        parts = [part for part in (name or "").strip().split() if part]
        if not parts:
            return "Unknown", "Lead"
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    @staticmethod
    def _extract_event_message(data: dict[str, Any]) -> str:
        for key in ["Message", "message", "query", "searchText", "text"]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _extract_vehicle_name(data: dict[str, Any]) -> str:
        for key in ["VehicleName", "vehicleName", "vehicle", "selectedVehicle"]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _extract_dwell_time_seconds(data: dict[str, Any]) -> int:
        for key in ["dwellTimeSeconds", "durationSeconds", "seconds", "duration"]:
            value = data.get(key)
            if value is None:
                continue
            try:
                parsed = int(float(value))
            except (TypeError, ValueError):
                continue
            return max(parsed, 0)
        return 0

    @staticmethod
    def _event_implies_test_drive(data: dict[str, Any]) -> bool:
        message = LeadService._extract_event_message(data).lower()
        return any(k in message for k in ["test drive", "drive the car", "see the car"])

    def _prepare_lead_state(self, dealership_id: str, payload: LeadCreateRequest) -> dict:
        now = datetime.utcnow()
        rule = self._dealership_rule(dealership_id)
        customer_location = payload.customer_location or self._infer_location(payload.message)
        normalized_signals = self._normalize_signals(payload.intent_signals, payload.message.lower())
        semantic_intent, intent_similarity = self.semantic.classify_intent(payload.message, payload.vehicle_interest)
        urgency, urgency_similarity = self.semantic.classify_urgency(payload.message)
        score = self._compute_score(normalized_signals, intent_similarity, urgency)
        temperature = "Hot" if score >= 80 else "Warm" if score >= 50 else "Cold"
        next_action, _ = self.semantic.choose_next_action(
            payload.message,
            payload.vehicle_interest,
            temperature,
            inventory_available=True,
            intent_label=semantic_intent,
            urgency_label=urgency,
        )
        duplicate = self.repo.find_hard_duplicate(
            dealership_id,
            email=payload.email,
            phone=payload.phone,
            crm_id=payload.crm_id,
        )
        return {
            "qualification": {
                "now": now,
                "rule": rule,
                "customer_location": customer_location,
                "normalized_signals": normalized_signals,
                "semantic_intent": semantic_intent,
                "intent_similarity": intent_similarity,
                "urgency": urgency,
                "urgency_similarity": urgency_similarity,
                "score": score,
                "temperature": temperature,
                "next_action": next_action,
                "duplicate": duplicate,
            },
            "duplicate_found": duplicate is not None,
        }

    def _assign_rep_from_state(self, state: dict) -> dict:
        qualification = state["qualification"]
        payload: LeadCreateRequest = state["payload"]
        rep = self.routing.assign_rep(
            state["dealership_id"],
            message=payload.message,
            vehicle_interest=payload.vehicle_interest,
            location=qualification["customer_location"],
            score=qualification["score"],
            reserve=True,
        )
        return {"assigned_rep": rep}

    def _merge_duplicate_from_state(self, state: dict) -> Lead:
        qualification = state["qualification"]
        duplicate: Lead = qualification["duplicate"]
        payload: LeadCreateRequest = state["payload"]
        normalized_signals: LeadIntentSignals = qualification["normalized_signals"]
        duplicate.message = payload.message
        duplicate.source_channel = payload.source_channel
        duplicate.vehicle_interest = payload.vehicle_interest
        duplicate.customer_location = payload.customer_location or duplicate.customer_location
        duplicate.budget_indicator = payload.budget_indicator or duplicate.budget_indicator
        duplicate.page_views = max(duplicate.page_views, normalized_signals.page_views)
        duplicate.vehicle_page_time_seconds = max(duplicate.vehicle_page_time_seconds, normalized_signals.vehicle_page_time_seconds)
        duplicate.chat_interactions += normalized_signals.chat_interactions
        duplicate.financing_inquiries += normalized_signals.financing_inquiries
        duplicate.trade_in_requests += normalized_signals.trade_in_requests
        duplicate.test_drive_interest = duplicate.test_drive_interest or normalized_signals.test_drive_interest
        duplicate.semantic_intent = qualification["semantic_intent"]
        duplicate.semantic_intent_similarity = max(duplicate.semantic_intent_similarity, qualification["intent_similarity"])
        duplicate.score = max(duplicate.score, qualification["score"])
        duplicate.temperature = "Hot" if duplicate.score >= 80 else "Warm" if duplicate.score >= 50 else "Cold"
        duplicate.urgency = qualification["urgency"] if qualification["urgency_similarity"] >= 0.45 else duplicate.urgency
        duplicate.next_action = qualification["next_action"]
        duplicate.status = "Working"
        duplicate.dedup_status = "merged"
        duplicate.merged_count += 1
        duplicate.last_customer_message_at = qualification["now"]
        created = self.repo.save(duplicate)
        self.crm.upsert_lead(created)
        self.sequences.ensure_sequence_for_lead(created)
        return created

    def _persist_new_from_state(self, state: dict) -> Lead:
        qualification = state["qualification"]
        payload: LeadCreateRequest = state["payload"]
        normalized_signals: LeadIntentSignals = qualification["normalized_signals"]
        rep = state.get("assigned_rep")
        rule = qualification["rule"]
        lead = Lead(
            dealership_id=state["dealership_id"],
            public_id=self.repo.next_public_id(state["dealership_id"]),
            crm_id=payload.crm_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            source_channel=payload.source_channel,
            vehicle_interest=payload.vehicle_interest,
            message=payload.message,
            customer_location=qualification["customer_location"],
            budget_indicator=payload.budget_indicator or self._infer_budget(payload.message),
            engagement_history=[{"ts": qualification["now"].isoformat(), "type": payload.source_channel, "message": payload.message}],
            previous_dealership_interactions=0,
            page_views=normalized_signals.page_views,
            vehicle_page_time_seconds=normalized_signals.vehicle_page_time_seconds,
            chat_interactions=normalized_signals.chat_interactions,
            financing_inquiries=normalized_signals.financing_inquiries,
            trade_in_requests=normalized_signals.trade_in_requests,
            test_drive_interest=normalized_signals.test_drive_interest,
            semantic_intent=qualification["semantic_intent"],
            semantic_intent_similarity=qualification["intent_similarity"],
            score=qualification["score"],
            temperature=qualification["temperature"],
            urgency=qualification["urgency"],
            assigned_rep=rep.name if rep else "Unassigned",
            assigned_rep_id=rep.public_id if rep else None,
            next_action=qualification["next_action"],
            status="Open",
            dedup_status="unique",
            merged_count=0,
            last_customer_message_at=qualification["now"],
            sla_due_at=qualification["now"] + timedelta(minutes=rule.response_sla_minutes if rule else self.settings.response_sla_minutes),
            created_at=qualification["now"],
            updated_at=qualification["now"],
        )
        created = self.repo.create(lead)
        self.crm.upsert_lead(created)
        self.sequences.ensure_sequence_for_lead(created)
        return created

    def _compute_score(self, signals: LeadIntentSignals, intent_similarity: float, urgency: str) -> int:
        behavioral = 0
        behavioral += min(signals.page_views, 10) * 2
        behavioral += min(signals.vehicle_page_time_seconds, 600) // 30
        behavioral += min(signals.chat_interactions, 5) * 4
        behavioral += min(signals.financing_inquiries, 3) * 7
        behavioral += min(signals.trade_in_requests, 2) * 7
        if signals.test_drive_interest:
            behavioral += 15
        behavioral = min(behavioral, 70)
        semantic = int(max(min(intent_similarity, 1.0), 0.0) * 20)
        urgency_bonus = {
            "Escalation": 12,
            "Immediate": 10,
            "High_Intent": 8,
            "Short-Term": 5,
            "Research Phase": 0,
            "Opt_Out": -10,
        }.get(urgency, 0)
        return min(100, behavioral + semantic + urgency_bonus)

    def _normalize_signals(self, signals: LeadIntentSignals, message: str) -> LeadIntentSignals:
        normalized = signals.model_copy(deep=True)
        if normalized.chat_interactions == 0 and message:
            normalized.chat_interactions = 1
        if normalized.financing_inquiries == 0 and any(k in message for k in ["finance", "financing", "loan", "emi"]):
            normalized.financing_inquiries = 1
        if normalized.trade_in_requests == 0 and any(k in message for k in ["trade-in", "trade in", "exchange"]):
            normalized.trade_in_requests = 1
        if not normalized.test_drive_interest and any(k in message for k in ["test drive", "drive the car", "see the car"]):
            normalized.test_drive_interest = True
        return normalized

    def _infer_location(self, message: str) -> str:
        lowered = message.lower()
        for city in [
            "austin",
            "dallas",
            "houston",
            "phoenix",
            "scottsdale",
            "denver",
            "miami",
            "orlando",
            "tampa",
            "atlanta",
            "charlotte",
            "raleigh",
            "nashville",
            "columbus",
            "hyderabad",
        ]:
            if city in lowered:
                return city.title()
        return "Unknown"

    def _infer_budget(self, message: str) -> str:
        lowered = message.lower()
        if any(token in lowered for token in ["budget", "price", "emi", "loan", "finance"]):
            return "Budget discussed"
        return "Unknown"

    def _run_response_time_monitor(self, dealership_id: str) -> None:
        overdue = self.repo.list_open_unresponded(dealership_id)
        changed = False
        for lead in overdue:
            if lead.escalated_at is None:
                lead.escalated_at = datetime.utcnow()
                lead.status = "Escalated"
                changed = True
        if changed:
            self.db.commit()

    def _dealership_rule(self, dealership_id: str) -> DealershipRule | None:
        return self.db.query(DealershipRule).filter(DealershipRule.dealership_id == dealership_id).first()
