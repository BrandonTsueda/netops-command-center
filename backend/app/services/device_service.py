import json
import logging
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate

logger = logging.getLogger(__name__)


def _dump_list(value: list[str] | list[int]) -> str:
    return json.dumps(value)


def _load_list(value: str | None) -> list:
    if not value:
        return []
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    except json.JSONDecodeError:
        return []


def to_device_read(device: Device) -> DeviceRead:
    return DeviceRead(
        id=device.id,
        hostname=device.hostname,
        ip_address=device.ip_address,
        role=device.role,
        site=device.site,
        platform=device.platform,
        owner=device.owner,
        tags=_load_list(device.tags),
        connection_type=device.connection_type,
        tcp_ports=_load_list(device.tcp_ports),
        http_urls=_load_list(device.http_urls),
        ssh_enabled=device.ssh_enabled,
        notes=device.notes,
        is_active=device.is_active,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def list_devices(db: Session, search: str | None = None, active_only: bool = False) -> tuple[list[DeviceRead], int]:
    statement = select(Device)
    count_statement = select(func.count()).select_from(Device)

    filters = []
    if active_only:
        filters.append(Device.is_active.is_(True))
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            (Device.hostname.ilike(pattern))
            | (Device.ip_address.ilike(pattern))
            | (Device.role.ilike(pattern))
            | (Device.site.ilike(pattern))
        )

    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    devices = db.scalars(statement.order_by(Device.site, Device.hostname)).all()
    total = db.scalar(count_statement) or 0
    return [to_device_read(device) for device in devices], total


def get_device(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise NotFoundError(f"Device {device_id} was not found.")
    return device


def create_device(db: Session, payload: DeviceCreate) -> DeviceRead:
    device = Device(
        hostname=payload.hostname,
        ip_address=payload.ip_address,
        role=payload.role,
        site=payload.site,
        platform=payload.platform,
        owner=payload.owner,
        tags=_dump_list(payload.tags),
        connection_type=payload.connection_type,
        tcp_ports=_dump_list(payload.tcp_ports),
        http_urls=_dump_list(payload.http_urls),
        ssh_enabled=payload.ssh_enabled,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(device)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Device create conflict for hostname=%s ip=%s", payload.hostname, payload.ip_address)
        raise ConflictError("A device with that hostname and IP address already exists.") from exc
    db.refresh(device)
    logger.info("Created device id=%s hostname=%s ip=%s", device.id, device.hostname, device.ip_address)
    return to_device_read(device)


def update_device(db: Session, device_id: int, payload: DeviceUpdate) -> DeviceRead:
    device = get_device(db, device_id)
    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        if field in {"tags", "tcp_ports", "http_urls"}:
            setattr(device, field, _dump_list(value or []))
        else:
            setattr(device, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A device with that hostname and IP address already exists.") from exc
    db.refresh(device)
    logger.info("Updated device id=%s hostname=%s", device.id, device.hostname)
    return to_device_read(device)


def delete_device(db: Session, device_id: int) -> None:
    device = get_device(db, device_id)
    db.delete(device)
    db.commit()
    logger.info("Deleted device id=%s hostname=%s", device.id, device.hostname)
