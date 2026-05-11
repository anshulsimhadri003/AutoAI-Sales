from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api_gateway.services.dashboard_service import DashboardService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.dashboard import AppointmentMetrics, LeadMetrics, SequenceMetrics

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/lead-metrics", response_model=LeadMetrics)
def lead_metrics(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return DashboardService(db).lead_metrics(dealership_id)

@router.get("/sequence-metrics", response_model=SequenceMetrics)
def sequence_metrics(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return DashboardService(db).sequence_metrics(dealership_id)

@router.get("/appointment-metrics", response_model=AppointmentMetrics)
def appointment_metrics(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return DashboardService(db).appointment_metrics(dealership_id)


@router.get("/overview")
def dashboard_overview(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return DashboardService(db).overview(dealership_id)
