from sqlalchemy.orm import Session

from app.schemas.automation import TriageResult
from app.services.automation_service import run_diagnostics
from app.services.dashboard_service import get_dashboard_summary
from app.services.incident_service import open_incident, resolve_device_incidents
from app.services.notification_service import send_notification


def triage_failed_checks(db: Session) -> TriageResult:
    summary = get_dashboard_summary(db)
    affected = [device for device in summary.devices if device.status in {"warning", "critical"}]
    healthy_ids = {device.device_id for device in summary.devices if device.status == "healthy"}

    incidents_opened = 0
    automation_results = []

    for device in affected:
        failed = [check for check in summary.failed_checks if check.device_id == device.device_id]
        details = "\n".join(f"- {check.check_type} {check.target}: {check.status} - {check.message}" for check in failed)
        _, created = open_incident(
            db=db,
            device_id=device.device_id,
            severity=device.status,
            title=f"{device.hostname} requires NOC triage",
            description=details or f"{device.hostname} status is {device.status}.",
        )
        if created:
            incidents_opened += 1

        runbook_id = "proxmox_diagnostics" if "proxmox" in device.role.lower() else "linux_basic_diagnostics"
        automation_results.append(run_diagnostics(db=db, device_id=device.device_id, runbook_id=runbook_id))

    resolved = resolve_device_incidents(db=db, healthy_device_ids=healthy_ids)
    notification_sent = False
    if affected:
        message = "\n".join(f"- {device.hostname}: {device.status}" for device in affected)
        notification_sent = send_notification("NetOps triage started", message)

    return TriageResult(
        status="completed",
        checked_devices=len(summary.devices),
        affected_devices=len(affected),
        incidents_opened=incidents_opened,
        incidents_resolved=resolved,
        automation_results=automation_results,
        notification_sent=notification_sent,
    )
