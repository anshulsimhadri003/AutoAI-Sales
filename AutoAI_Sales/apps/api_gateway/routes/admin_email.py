from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api_gateway.services.email_dispatch_service import EmailDispatchService
from shared.auth.deps import require_admin_token
from shared.db.session import get_db
from shared.integrations.email_client import EmailClient

router = APIRouter(prefix="/api/v1/admin/email", tags=["admin-email"])


class TestEmailRequest(BaseModel):
    to_email: str
    subject: str = "Halcyon SMTP Test"


@router.post("/test")
def send_test_email(
    payload: TestEmailRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    del db
    ok = EmailClient().send_test_email(payload.to_email, payload.subject)
    return {"success": ok}


@router.post("/reminders/run")
def run_due_email_reminders(
    dealership_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
):
    return EmailDispatchService(db).send_due_appointment_reminders(dealership_id)