from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth.deps import get_dealership_id, require_site_api_key
from shared.db.session import get_db
from shared.repositories.worker_repository import WorkerRepository
from shared.schemas.workers import WorkerConfigResponse

router = APIRouter(prefix="/api/v1/workers", tags=["workers"])

@router.get("", response_model=list[WorkerConfigResponse])
def list_workers(
    dealership_id: str = Depends(get_dealership_id),
    db: Session = Depends(get_db),
    _: None = Depends(require_site_api_key),
):
    return WorkerRepository(db).list_all(dealership_id)
