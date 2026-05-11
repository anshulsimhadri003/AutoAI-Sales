from sqlalchemy.orm import Session
from shared.models.models import WorkerConfig

class WorkerRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, dealership_id: str):
        return (
            self.db.query(WorkerConfig)
            .filter(WorkerConfig.dealership_id == dealership_id)
            .order_by(WorkerConfig.id.asc())
            .all()
        )
