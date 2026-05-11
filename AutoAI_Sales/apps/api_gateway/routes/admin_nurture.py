from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api_gateway.services.nurture_dispatch_service import NurtureDispatchService
from shared.auth.deps import require_admin_token
from shared.db.session import get_db

router = APIRouter(prefix="/api/v1/admin/nurture", tags=["admin-nurture"])


@router.post("/run")
def run_due_nurture_sequences(
    dealership_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    return NurtureDispatchService(db).run_due_sequences(dealership_id)