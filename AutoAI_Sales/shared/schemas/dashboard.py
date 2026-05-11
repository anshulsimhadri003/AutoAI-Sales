from pydantic import BaseModel


class LeadMetrics(BaseModel):
    leads_processed: int
    avg_response_time: str
    hot_leads: int
    active_conversations: int


class SequenceMetrics(BaseModel):
    active_sequences: int
    engagement_rate: str
    response_rate: str
    escalations: int


class AppointmentMetrics(BaseModel):
    appointments_scheduled: int
    show_rate: str
    no_show_rate: str
    reschedules: int
