from fastapi import APIRouter

from shared.db.session import db_ready

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check():
    db_ready()
    return {"status": "ready"}
