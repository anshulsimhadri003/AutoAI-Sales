from datetime import datetime
from pydantic import BaseModel


class SlotResponse(BaseModel):
    start: str
    end: str


class AppointmentBookRequest(BaseModel):
    lead_id: str
    vehicle_id: str
    rep_id: str
    start_time: str
    end_time: str
    channel: str


class AppointmentRescheduleRequest(BaseModel):
    appointment_id: str
    new_vehicle_id: str | None = None
    start_time: str
    end_time: str


class AppointmentResponse(BaseModel):
    public_id: str
    dealership_id: str
    lead_id: str
    vehicle_id: str
    rep_id: str
    start_time: str
    end_time: str
    channel: str
    status: str
    vehicle_location: str
    vehicle_status: str
    attendance_status: str
    created_at: datetime

    model_config = {"from_attributes": True}
