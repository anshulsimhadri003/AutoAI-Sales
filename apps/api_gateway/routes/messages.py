from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api_gateway.services.nurture_service import NurtureService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.messages import AIReplyRequest, AIReplyResponse

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

@router.post("/reply", response_model=AIReplyResponse)
def generate_reply(
    payload: AIReplyRequest,
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return NurtureService(db).generate_reply(dealership_id, payload)
