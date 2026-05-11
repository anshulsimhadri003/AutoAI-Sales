from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api_gateway.services.lead_service import LeadService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.leads import (
    LeadAgentResponseRequest,
    LeadAssignRequest,
    LeadCreateRequest,
    LeadResponse,
    LeadScoreBreakdown,
    LeadTimelineItem,
)

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


@router.get("/{lead_id}/timeline", response_model=list[LeadTimelineItem])
def get_lead_timeline(
    lead_id: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    timeline = LeadService(db).get_timeline(dealership_id, lead_id)
    if not timeline:
        lead = LeadService(db).get_lead(dealership_id, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
    return timeline


@router.get("/{lead_id}/score-breakdown", response_model=LeadScoreBreakdown)
def get_lead_score_breakdown(
    lead_id: str,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    breakdown = LeadService(db).get_score_breakdown(dealership_id, lead_id)
    if not breakdown:
        raise HTTPException(status_code=404, detail="Lead not found")
    return breakdown


@router.post("/{lead_id}/respond", response_model=LeadResponse)
def register_agent_response(
    lead_id: str,
    payload: LeadAgentResponseRequest,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    lead = LeadService(db).register_agent_response(
        dealership_id, lead_id, channel=payload.channel, message=payload.message
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead(
    lead_id: str,
    payload: LeadAssignRequest,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    lead = LeadService(db).assign_lead(dealership_id, lead_id, rep_id=payload.rep_id, rep_name=payload.rep_name)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
