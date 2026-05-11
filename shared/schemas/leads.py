from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LeadIntentSignals(BaseModel):
    page_views: int = Field(default=0, ge=0)
    vehicle_page_time_seconds: int = Field(default=0, ge=0)
    chat_interactions: int = Field(default=0, ge=0)
    financing_inquiries: int = Field(default=0, ge=0)
    trade_in_requests: int = Field(default=0, ge=0)
    test_drive_interest: bool = False


class LeadCreateRequest(BaseModel):
    source_channel: str
    first_name: str
    last_name: str
    email: str
    phone: str
    vehicle_interest: str
    message: str
    crm_id: str | None = None
    customer_location: str | None = None
    budget_indicator: str | None = None
    intent_signals: LeadIntentSignals = Field(default_factory=LeadIntentSignals)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("email must be a valid email address")
        return cleaned


class LeadResponse(BaseModel):
    public_id: str
    dealership_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    source_channel: str
    vehicle_interest: str
    message: str
    customer_location: str
    budget_indicator: str
    intent_signals: LeadIntentSignals
    semantic_intent: str
    semantic_intent_similarity: float
    score: int
    temperature: str
    urgency: str
    assigned_rep: str
    next_action: str
    status: str
    dedup_status: str
    merged_count: int
    first_response_at: datetime | None
    sla_due_at: datetime
    escalated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

class LeadTimelineItem(BaseModel):
    timestamp: datetime | None = None
    type: str
    channel: str | None = None
    title: str
    description: str | None = None
    metadata: dict = Field(default_factory=dict)


class LeadScoreBreakdown(BaseModel):
    lead_id: str
    score: int
    temperature: str
    urgency: str
    semantic_intent: str
    components: dict[str, int | float | bool | str]
    reasons: list[str]


class LeadAgentResponseRequest(BaseModel):
    channel: str = "email"
    message: str = Field(min_length=1)


class LeadAssignRequest(BaseModel):
    rep_id: str = Field(min_length=1)
    rep_name: str = Field(min_length=1)

