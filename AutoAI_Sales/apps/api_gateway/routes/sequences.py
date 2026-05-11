from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api_gateway.services.nurture_service import NurtureService
from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.schemas.sequences import SequenceResponse

router = APIRouter(prefix="/api/v1/sequences", tags=["sequences"])

@router.get("", response_model=list[SequenceResponse])
def list_sequences(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return NurtureService(db).list_sequences(dealership_id)
