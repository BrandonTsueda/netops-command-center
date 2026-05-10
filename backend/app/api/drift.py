from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.drift import DriftEventList
from app.services import drift_service

router = APIRouter(prefix="/drift-events", tags=["drift-events"])


@router.get("", response_model=DriftEventList)
def list_drift_events(
    device_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> DriftEventList:
    items, total = drift_service.list_drift_events(db=db, device_id=device_id, limit=limit)
    return DriftEventList(items=items, total=total)
