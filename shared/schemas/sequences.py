from datetime import datetime

from pydantic import BaseModel


class SequenceResponse(BaseModel):
    public_id: str
    dealership_id: str
    name: str
    lead_name: str
    lead_public_id: str | None
    channel: str
    engagement: str
    status: str
    next_step: str
    current_step: int
    total_steps: int
    cadence_minutes: int
    paused_reason: str | None
    escalated: bool
    conversion_outcome: str | None
    next_run_at: datetime | None

    model_config = {"from_attributes": True}
