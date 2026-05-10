import logging
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.schemas.health_check import HealthCheckCreate, HealthCheckRead
from app.services.device_service import get_device

logger = logging.getLogger(__name__)


def create_health_check(db: Session, payload: HealthCheckCreate) -> HealthCheckRead:
    get_device(db, payload.device_id)
    result = CheckResult(**payload.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)
    logger.info(
        "Recorded health check id=%s device_id=%s type=%s status=%s",
        result.id,
        result.device_id,
        result.check_type,
        result.status,
    )
    return HealthCheckRead.model_validate(result)


def list_health_checks(db: Session, device_id: int | None = None, limit: int = 100) -> tuple[list[HealthCheckRead], int]:
    statement = select(CheckResult)
    count_statement = select(func.count()).select_from(CheckResult)

    if device_id is not None:
        statement = statement.where(CheckResult.device_id == device_id)
        count_statement = count_statement.where(CheckResult.device_id == device_id)

    total = db.scalar(count_statement) or 0
    results = db.scalars(statement.order_by(CheckResult.created_at.desc()).limit(limit)).all()
    return [HealthCheckRead.model_validate(result) for result in results], total
