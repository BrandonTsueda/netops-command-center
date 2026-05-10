from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.automation import (
    AutomationRequest,
    AutomationRunbookResult,
    AutomationRunList,
    RestartContainerRequest,
    RestartServiceRequest,
    RunbookRead,
    TriageResult,
)
from app.services import automation_service
from app.services.triage_service import triage_failed_checks

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/runbooks", response_model=list[RunbookRead])
def list_runbooks() -> list[RunbookRead]:
    return automation_service.list_runbooks()


@router.get("/runs", response_model=AutomationRunList)
def list_runs(
    device_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),
) -> AutomationRunList:
    items, total = automation_service.list_automation_runs(db=db, device_id=device_id, limit=limit)
    return AutomationRunList(items=items, total=total)


@router.post("/devices/{device_id}/diagnostics", response_model=AutomationRunbookResult)
def run_diagnostics(
    device_id: int,
    payload: AutomationRequest | None = None,
    runbook_id: str = "linux_basic_diagnostics",
    db: Session = Depends(get_db),
) -> AutomationRunbookResult:
    payload = payload or AutomationRequest()
    return automation_service.run_diagnostics(
        db=db,
        device_id=device_id,
        runbook_id=runbook_id,
        ssh_username=payload.ssh_username,
    )


@router.post("/devices/{device_id}/restart-service", response_model=AutomationRunbookResult)
def restart_service(
    device_id: int,
    payload: RestartServiceRequest,
    db: Session = Depends(get_db),
) -> AutomationRunbookResult:
    return automation_service.restart_service(
        db=db,
        device_id=device_id,
        service_name=payload.service_name,
        ssh_username=payload.ssh_username,
    )


@router.post("/devices/{device_id}/restart-container", response_model=AutomationRunbookResult)
def restart_container(
    device_id: int,
    payload: RestartContainerRequest,
    db: Session = Depends(get_db),
) -> AutomationRunbookResult:
    return automation_service.restart_container(
        db=db,
        device_id=device_id,
        container_name=payload.container_name,
        ssh_username=payload.ssh_username,
    )


@router.post("/devices/{device_id}/config-snapshot", response_model=AutomationRunbookResult)
def collect_config_snapshot(
    device_id: int,
    payload: AutomationRequest | None = None,
    db: Session = Depends(get_db),
) -> AutomationRunbookResult:
    payload = payload or AutomationRequest()
    return automation_service.collect_config_snapshot(db=db, device_id=device_id, ssh_username=payload.ssh_username)


@router.post("/triage", response_model=TriageResult)
def triage(db: Session = Depends(get_db)) -> TriageResult:
    return triage_failed_checks(db=db)
