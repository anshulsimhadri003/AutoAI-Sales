from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api_gateway.services.lead_service import LeadService
from shared.repositories.user_event_repository import UserEventRepository
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


@router.get("/session/{session_id}")
def list_session_events(
    session_id: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    events = UserEventRepository(db).list_for_session(dealership_id, session_id)
    return [
        {
            "public_id": event.public_id,
            "session_id": event.session_id,
            "lead_public_id": event.lead_public_id,
            "action": event.action,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at,
        }
        for event in events
    ]
