from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.incident import IncidentList
from app.services.incident_service import list_incidents

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=IncidentList)
def get_incidents(
    status: str | None = Query(default=None, pattern="^(open|resolved)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> IncidentList:
    items, total = list_incidents(db=db, status=status, limit=limit)
    return IncidentList(items=items, total=total)
