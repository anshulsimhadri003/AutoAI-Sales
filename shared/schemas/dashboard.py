from pydantic import BaseModel


class LeadMetrics(BaseModel):
    leads_processed: int
    avg_response_time: str
    hot_leads: int
    active_conversations: int
    conversion_rate: str = "0%"
    sla_breached: int = 0
    pending_response: int = 0


class SequenceMetrics(BaseModel):
    active_sequences: int
    engagement_rate: str
    response_rate: str
    escalations: int
    messages_sent: int = 0
    opens: int = 0
    clicks: int = 0
    replies: int = 0


class AppointmentMetrics(BaseModel):
    appointments_scheduled: int
    show_rate: str
    no_show_rate: str
    reschedules: int
    confirmed: int = 0
    shows: int = 0
    no_shows: int = 0
