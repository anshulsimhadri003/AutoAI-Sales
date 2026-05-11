from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api_gateway.services.lead_service import LeadService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.lead_events import LeadEventRequest, LeadEventResponse

router = APIRouter(prefix="/api/lead/event", tags=["lead-events"])


@router.post("", response_model=LeadEventResponse, status_code=status.HTTP_201_CREATED)
def process_lead_event(
    payload: LeadEventRequest,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return LeadService(db).handle_lead_event(dealership_id, payload)
