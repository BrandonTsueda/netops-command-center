from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health_check import FleetCheckRun, HealthCheckCreate, HealthCheckList, HealthCheckRead
from app.services.check_engine import run_fleet_checks
from app.services import health_check_service
from app.services.triage_service import triage_failed_checks

router = APIRouter(prefix="/health-checks", tags=["health-checks"])


@router.get("", response_model=HealthCheckList)
def list_health_checks(
    device_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> HealthCheckList:
    items, total = health_check_service.list_health_checks(db=db, device_id=device_id, limit=limit)
    return HealthCheckList(items=items, total=total)


@router.post("", response_model=HealthCheckRead, status_code=status.HTTP_201_CREATED)
def create_health_check(payload: HealthCheckCreate, db: Session = Depends(get_db)) -> HealthCheckRead:
    return health_check_service.create_health_check(db=db, payload=payload)


@router.post("/run", response_model=FleetCheckRun)
async def run_checks_for_fleet(
    active_only: bool = True,
    auto_triage: bool = False,
    db: Session = Depends(get_db),
) -> FleetCheckRun:
    result = await run_fleet_checks(db=db, active_only=active_only)
    if auto_triage:
        triage_failed_checks(db=db)
    return result
