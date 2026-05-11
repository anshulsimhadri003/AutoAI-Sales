from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


class Dealership(Base):
    __tablename__ = "dealerships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkerConfig(Base):
    __tablename__ = "worker_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    worker_key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    tagline: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000))


class SalesRep(Base):
    __tablename__ = "sales_reps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(100), default="Hyderabad")
    specializations: Mapped[list[str]] = mapped_column(JSON, default=list)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    profile_text: Mapped[str] = mapped_column(Text, default="")
    workload: Mapped[int] = mapped_column(Integer, default=0)
    max_active_leads: Mapped[int] = mapped_column(Integer, default=20)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    manager_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    available_start_hour: Mapped[int] = mapped_column(Integer, default=10)
    available_end_hour: Mapped[int] = mapped_column(Integer, default=19)


class VehicleInventory(Base):
    __tablename__ = "vehicle_inventory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    stock_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    make_model: Mapped[str] = mapped_column(String(255))
    trim: Mapped[str] = mapped_column(String(255), default="")
    year: Mapped[int] = mapped_column(Integer, default=0)
    body_type: Mapped[str] = mapped_column(String(100), default="")
    fuel_type: Mapped[str] = mapped_column(String(50), default="")
    transmission: Mapped[str] = mapped_column(String(50), default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    price_band: Mapped[str] = mapped_column(String(100), default="")
    color: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(50), default="available")
    available_for_test_drive: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    crm_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    external_vehicle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_vehicle_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_year: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vehicle_make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(50), index=True)
    source_channel: Mapped[str] = mapped_column(String(50))
    vehicle_interest: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(String(2000))
    customer_location: Mapped[str] = mapped_column(String(100), default="Unknown")
    budget_indicator: Mapped[str] = mapped_column(String(100), default="Unknown")
    engagement_history: Mapped[list[dict]] = mapped_column(JSON, default=list)
    previous_dealership_interactions: Mapped[int] = mapped_column(Integer, default=0)
    page_views: Mapped[int] = mapped_column(Integer, default=0)
    vehicle_page_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    chat_interactions: Mapped[int] = mapped_column(Integer, default=0)
    financing_inquiries: Mapped[int] = mapped_column(Integer, default=0)
    trade_in_requests: Mapped[int] = mapped_column(Integer, default=0)
    test_drive_interest: Mapped[bool] = mapped_column(Boolean, default=False)
    semantic_intent: Mapped[str] = mapped_column(String(100), default="general_interest")
    semantic_intent_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    score: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[str] = mapped_column(String(20))
    urgency: Mapped[str] = mapped_column(String(30))
    assigned_rep: Mapped[str] = mapped_column(String(100))
    assigned_rep_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_action: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="Open")
    dedup_status: Mapped[str] = mapped_column(String(50), default="unique")
    merged_into_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merged_count: Mapped[int] = mapped_column(Integer, default=0)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_customer_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_agent_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=5))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def intent_signals(self) -> dict[str, int | bool]:
        return {
            "page_views": self.page_views,
            "vehicle_page_time_seconds": self.vehicle_page_time_seconds,
            "chat_interactions": self.chat_interactions,
            "financing_inquiries": self.financing_inquiries,
            "trade_in_requests": self.trade_in_requests,
            "test_drive_interest": self.test_drive_interest,
        }

    @property
    def intent_signals_model(self):
        from shared.schemas.leads import LeadIntentSignals

        return LeadIntentSignals(**self.intent_signals)


class Sequence(Base):
    __tablename__ = "sequences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    lead_name: Mapped[str] = mapped_column(String(255))
    lead_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    definition_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(50))
    engagement: Mapped[str] = mapped_column(String(50), default="Low")
    status: Mapped[str] = mapped_column(String(50), default="Active")
    next_step: Mapped[str] = mapped_column(String(255), default="Initial response")
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    total_steps: Mapped[int] = mapped_column(Integer, default=4)
    cadence_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    current_template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paused_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    conversion_outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_message_classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageEvent(Base):
    __tablename__ = "message_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    sequence_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lead_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(50), default="email")
    direction: Mapped[str] = mapped_column(String(20), default="outbound")
    template_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(50), default="sent")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



class UserEvent(Base):
    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    lead_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    lead_id: Mapped[str] = mapped_column(String(64), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(64), index=True)
    rep_id: Mapped[str] = mapped_column(String(64), index=True)
    start_time: Mapped[str] = mapped_column(String(64))
    end_time: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="Confirmed")
    vehicle_location: Mapped[str] = mapped_column(String(100), default="")
    vehicle_status: Mapped[str] = mapped_column(String(50), default="available")
    attendance_status: Mapped[str] = mapped_column(String(32), default="scheduled")
    rescheduled_from_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppointmentReminder(Base):
    __tablename__ = "appointment_reminders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    appointment_public_id: Mapped[str] = mapped_column(String(64), index=True)
    reminder_type: Mapped[str] = mapped_column(String(32))
    channel: Mapped[str] = mapped_column(String(32), default="email")
    due_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DealershipRule(Base):
    __tablename__ = "dealership_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    response_sla_minutes: Mapped[int] = mapped_column(Integer, default=5)
    max_leads_per_rep: Mapped[int] = mapped_column(Integer, default=20)
    allow_after_hours_booking: Mapped[bool] = mapped_column(Boolean, default=False)
    default_test_drive_duration_mins: Mapped[int] = mapped_column(Integer, default=30)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class StoreHour(Base):
    __tablename__ = "store_hours"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    day_of_week: Mapped[str] = mapped_column(String(16), index=True)
    open_time: Mapped[str] = mapped_column(String(8), default="")
    close_time: Mapped[str] = mapped_column(String(8), default="")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class RepAvailability(Base):
    __tablename__ = "rep_availability"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rep_id: Mapped[str] = mapped_column(String(64), index=True)
    dealership_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[str] = mapped_column(String(16), index=True)
    start_time: Mapped[str] = mapped_column(String(8))
    end_time: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32), default="available")


class SequenceDefinition(Base):
    __tablename__ = "sequence_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    channel: Mapped[str] = mapped_column(String(50), default="email")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(64), index=True)


class SequenceStepDefinition(Base):
    __tablename__ = "sequence_step_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sequence_public_id: Mapped[str] = mapped_column(String(64), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    delay_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    template_id: Mapped[str] = mapped_column(String(64))
    condition_type: Mapped[str] = mapped_column(String(64), default="always")
    condition_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
