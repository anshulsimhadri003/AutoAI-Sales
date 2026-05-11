from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api_gateway.services.appointment_service import AppointmentService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.appointments import (
    AppointmentBookRequest,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    SlotResponse,
)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return AppointmentService(db).list_appointments(dealership_id)


@router.get("/slots", response_model=list[SlotResponse])
def get_slots(
    vehicle_id: str,
    date: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return AppointmentService(db).get_slots(dealership_id, vehicle_id, date)


@router.post("/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: AppointmentBookRequest,
    background_tasks: BackgroundTasks,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    try:
        return AppointmentService(db).book_appointment(dealership_id, payload, background_tasks)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/reschedule", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def reschedule_appointment(
    payload: AppointmentRescheduleRequest,
    background_tasks: BackgroundTasks,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    try:
        return AppointmentService(db).reschedule_appointment(dealership_id, payload, background_tasks)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))



@router.post("/{appointment_id}/mark-show", response_model=AppointmentResponse)
def mark_show(
    appointment_id: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    appointment = AppointmentService(db).mark_attendance(dealership_id, appointment_id, "show")
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.post("/{appointment_id}/mark-no-show", response_model=AppointmentResponse)
def mark_no_show(
    appointment_id: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    appointment = AppointmentService(db).mark_attendance(dealership_id, appointment_id, "no_show")
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment
