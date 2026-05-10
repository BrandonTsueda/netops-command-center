from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.incident import Incident
from app.schemas.incident import IncidentRead


def list_incidents(db: Session, status: str | None = None, limit: int = 100) -> tuple[list[IncidentRead], int]:
    statement = select(Incident)
    count_statement = select(func.count()).select_from(Incident)
    if status:
        statement = statement.where(Incident.status == status)
        count_statement = count_statement.where(Incident.status == status)
    total = db.scalar(count_statement) or 0
    rows = db.scalars(statement.order_by(Incident.opened_at.desc()).limit(limit)).all()
    return [IncidentRead.model_validate(row) for row in rows], total


def open_incident(db: Session, device_id: int, severity: str, title: str, description: str) -> tuple[Incident, bool]:
    existing = db.scalars(
        select(Incident)
        .where(Incident.device_id == device_id)
        .where(Incident.status == "open")
        .where(Incident.title == title)
        .limit(1)
    ).first()
    if existing:
        existing.severity = severity
        existing.description = description
        db.commit()
        db.refresh(existing)
        return existing, False

    incident = Incident(device_id=device_id, severity=severity, title=title, description=description, status="open")
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident, True


def resolve_device_incidents(db: Session, healthy_device_ids: set[int]) -> int:
    if not healthy_device_ids:
        return 0
    rows = db.scalars(
        select(Incident)
        .where(Incident.status == "open")
        .where(Incident.device_id.in_(healthy_device_ids))
    ).all()
    for row in rows:
        row.status = "resolved"
        row.resolved_at = utc_now()
    db.commit()
    return len(rows)
