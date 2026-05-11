from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.schemas.leads import LeadIntentSignals


TRACK_EVENT_TYPES = {
    "CHATBOT_AUTO_OPEN",
    "CHATBOT_CONVERSATION",
    "CHATBOT_LEAD",
    "CHATBOT_LEAD_SUBMITTED",
    "FILTER_APPLIED",
    "HEARTBEAT",
    "INVENTORY_DWELL_TIME",
    "INVENTORY_FILTER_APPLIED",
    "INVENTORY_SESSION_START",
    "INVENTORY_SESSION_END",
    "SCROLL_DEPTH",
    "SEARCH",
    "VEHICLE_CLICK",
}


class ExternalLeadCreateData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    Name: str = Field(min_length=1)
    PhoneNumber: str = Field(min_length=1)
    Email: str = Field(min_length=3)
    Address: str | None = None
    SessionId: str | None = None
    VehicleId: int | str | None = None
    VehicleName: str = Field(min_length=1)
    Vin: str | None = None
    Year: str | None = None
    Make: str | None = None
    Model: str | None = None
    Message: str = ""

    @field_validator("Email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("Email must be a valid email address")
        return cleaned


class LeadEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["CREATE_LEAD", "TRACK_EVENT"]
    sessionId: str = Field(min_length=1)
    eventType: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "TRACK_EVENT":
            if not self.eventType:
                raise ValueError("eventType is required when action=TRACK_EVENT")
            if self.eventType not in TRACK_EVENT_TYPES:
                raise ValueError(f"Unsupported eventType: {self.eventType}")
        else:
            # Validate exact lead payload shape and field casing for CREATE_LEAD.
            lead_data = ExternalLeadCreateData.model_validate(self.data)
            if lead_data.SessionId and lead_data.SessionId != self.sessionId:
                raise ValueError("SessionId inside data must match top-level sessionId")
        return self


class LeadSnapshotResponse(BaseModel):
    public_id: str
    session_id: str | None = None
    full_name: str
    email: str
    phone: str
    vehicle_interest: str
    score: int
    temperature: str
    urgency: str
    assigned_rep: str
    status: str
    intent_signals: LeadIntentSignals


class LeadEventResponse(BaseModel):
    action: str
    sessionId: str
    eventType: str | None = None
    userEventId: str
    leadPublicId: str | None = None
    status: str
    detail: str
    processedAt: datetime
    lead: LeadSnapshotResponse | None = None
