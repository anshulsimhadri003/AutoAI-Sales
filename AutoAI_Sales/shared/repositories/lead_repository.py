from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from shared.models.models import Lead
from shared.utils.ids import make_public_id


class LeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, dealership_id: str):
        return (
            self.db.query(Lead)
            .filter(Lead.dealership_id == dealership_id, Lead.merged_into_public_id.is_(None))
            .order_by(Lead.id.desc())
            .all()
        )

    def get_by_public_id(self, dealership_id: str, public_id: str):
        return (
            self.db.query(Lead)
            .filter(Lead.dealership_id == dealership_id, Lead.public_id == public_id)
            .first()
        )

    def get_by_session_id(self, dealership_id: str, session_id: str):
        return (
            self.db.query(Lead)
            .filter(
                Lead.dealership_id == dealership_id,
                Lead.session_id == session_id,
                Lead.merged_into_public_id.is_(None),
            )
            .order_by(Lead.id.desc())
            .first()
        )

    def create(self, lead: Lead):
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def save(self, lead: Lead):
        lead.updated_at = datetime.utcnow()
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def find_hard_duplicate(self, dealership_id: str, *, email: str, phone: str, crm_id: str | None = None):
        filters = []
        if email:
            filters.append(func.lower(Lead.email) == email.lower())
        if phone:
            filters.append(Lead.phone == phone)
        if crm_id:
            filters.append(Lead.crm_id == crm_id)
        if not filters:
            return None
        return (
            self.db.query(Lead)
            .filter(
                Lead.dealership_id == dealership_id,
                Lead.merged_into_public_id.is_(None),
                or_(*filters),
            )
            .order_by(Lead.id.asc())
            .first()
        )

    def count_open(self, dealership_id: str) -> int:
        return (
            self.db.query(Lead)
            .filter(
                Lead.dealership_id == dealership_id,
                Lead.merged_into_public_id.is_(None),
                Lead.status.in_(["Open", "Working", "Escalated"]),
            )
            .count()
        )

    def list_open_unresponded(self, dealership_id: str):
        now = datetime.utcnow()
        return (
            self.db.query(Lead)
            .filter(
                Lead.dealership_id == dealership_id,
                Lead.merged_into_public_id.is_(None),
                Lead.first_response_at.is_(None),
                Lead.sla_due_at <= now,
                Lead.status.in_(["Open", "Working"]),
            )
            .all()
        )

    def next_public_id(self, dealership_id: str) -> str:
        return make_public_id("LD")
