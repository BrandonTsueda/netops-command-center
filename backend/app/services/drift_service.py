import json
import logging
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.device import Device
from app.models.drift_event import DriftEvent
from app.schemas.drift import DriftEventRead

logger = logging.getLogger(__name__)


def record_drift_for_run(
    db: Session,
    device: Device,
    previous_results: dict[str, CheckResult],
    current_results: list[CheckResult],
) -> list[DriftEvent]:
    events: list[DriftEvent] = []
    current_by_key = {
        json.dumps({"check_type": result.check_type, "target": result.target}, sort_keys=True): result
        for result in current_results
    }

    for key, current in current_by_key.items():
        previous = previous_results.get(key)
        if previous and previous.status != current.status:
            severity = "critical" if current.status == "critical" else "info" if current.status == "healthy" else "warning"
            events.append(
                DriftEvent(
                    device_id=device.id,
                    event_type="status_change",
                    severity=severity,
                    title=f"{device.hostname} {current.check_type} status changed",
                    description=f"{current.target} changed from {previous.status} to {current.status}.",
                    previous_value=previous.status,
                    current_value=current.status,
                )
            )
        elif not previous and current.check_type in {"tcp", "ssh", "http"}:
            events.append(
                DriftEvent(
                    device_id=device.id,
                    event_type="service_observed",
                    severity="info",
                    title=f"{device.hostname} service observed",
                    description=f"{current.check_type.upper()} check target {current.target} is now being tracked.",
                    previous_value=None,
                    current_value=current.status,
                )
            )

    if events:
        db.add_all(events)
        db.commit()
        for event in events:
            db.refresh(event)
        logger.info("Recorded %s drift events for device id=%s", len(events), device.id)
    return events


def list_drift_events(db: Session, device_id: int | None = None, limit: int = 100) -> tuple[list[DriftEventRead], int]:
    statement = select(DriftEvent)
    count_statement = select(func.count()).select_from(DriftEvent)
    if device_id is not None:
        statement = statement.where(DriftEvent.device_id == device_id)
        count_statement = count_statement.where(DriftEvent.device_id == device_id)
    total = db.scalar(count_statement) or 0
    rows = db.scalars(statement.order_by(DriftEvent.created_at.desc()).limit(limit)).all()
    return [DriftEventRead.model_validate(row) for row in rows], total
