from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.device import Device
from app.models.drift_event import DriftEvent
from app.schemas.dashboard import DashboardSummary, DeviceStatusSummary
from app.schemas.drift import DriftEventRead
from app.schemas.health_check import HealthCheckRead
from app.services.check_engine import STATUS_RANK
from app.services.device_service import _load_list


def get_dashboard_summary(db: Session) -> DashboardSummary:
    devices = db.scalars(select(Device).order_by(Device.site, Device.hostname)).all()
    summaries = [_summarize_device(db, device) for device in devices]

    counts = {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0}
    for summary in summaries:
        counts[summary.status] += 1

    recent_checks = db.scalars(
        select(CheckResult)
        .order_by(CheckResult.created_at.desc())
        .limit(500)
    ).all()
    expected_by_device = {device.id: _expected_keys(device) for device in devices}
    latest_expected: dict[str, CheckResult] = {}
    for row in recent_checks:
        key = f"{row.device_id}:{row.check_type}:{row.target}"
        expected_key = f"{row.check_type}:{row.target}"
        if expected_key in expected_by_device.get(row.device_id, set()) and key not in latest_expected:
            latest_expected[key] = row
    failed = [row for row in latest_expected.values() if row.status in {"warning", "critical"}][:20]
    drift = db.scalars(
        select(DriftEvent)
        .where(DriftEvent.severity != "info")
        .where(DriftEvent.event_type != "service_removed")
        .where(~((DriftEvent.event_type == "status_change") & (DriftEvent.current_value == "healthy")))
        .order_by(DriftEvent.created_at.desc())
        .limit(20)
    ).all()

    return DashboardSummary(
        total_devices=len(devices),
        active_devices=sum(1 for device in devices if device.is_active),
        failed_checks=[HealthCheckRead.model_validate(row) for row in failed],
        recent_drift=[DriftEventRead.model_validate(row) for row in drift],
        devices=summaries,
        **counts,
    )


def _summarize_device(db: Session, device: Device) -> DeviceStatusSummary:
    recent = db.scalars(
        select(CheckResult)
        .where(CheckResult.device_id == device.id)
        .order_by(CheckResult.created_at.desc())
        .limit(50)
    ).all()
    latest_by_target: dict[str, CheckResult] = {}
    expected_keys = _expected_keys(device)
    for row in recent:
        key = f"{row.check_type}:{row.target}"
        if key in expected_keys and key not in latest_by_target:
            latest_by_target[key] = row

    latest = list(latest_by_target.values())
    status = "unknown"
    if latest:
        status = max((row.status for row in latest), key=lambda value: STATUS_RANK.get(value, 1))

    total_checks = len(recent)
    successful = sum(1 for row in recent if row.status == "healthy")
    availability = round((successful / total_checks) * 100, 2) if total_checks else 0.0

    return DeviceStatusSummary(
        device_id=device.id,
        hostname=device.hostname,
        ip_address=device.ip_address,
        role=device.role,
        site=device.site,
        status=status,
        last_check_at=recent[0].created_at if recent else None,
        failed_checks=sum(1 for row in latest if row.status in {"warning", "critical"}),
        total_checks=total_checks,
        availability_percent=availability,
    )


def _expected_keys(device: Device) -> set[str]:
    keys: set[str] = set()
    if device.connection_type in {"icmp", "agent", "manual"}:
        keys.add(f"ping:{device.ip_address}")
    tcp_ports = [int(port) for port in _load_list(device.tcp_ports)]
    for port in tcp_ports:
        keys.add(f"tcp:{device.ip_address}:{port}")
    if device.ssh_enabled and 22 not in tcp_ports:
        keys.add(f"ssh:{device.ip_address}:22")
    for url in _load_list(device.http_urls):
        keys.add(f"http:{url}")
    if not keys:
        keys.add(f"inventory:{device.ip_address}")
    return keys
