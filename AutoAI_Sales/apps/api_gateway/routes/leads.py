from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api_gateway.services.lead_service import LeadService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.leads import LeadCreateRequest, LeadResponse

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])

@router.get("", response_model=list[LeadResponse])
def list_leads(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return LeadService(db).list_leads(dealership_id)

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreateRequest,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return LeadService(db).create_lead(dealership_id, payload)

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    lead = LeadService(db).get_lead(dealership_id, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
