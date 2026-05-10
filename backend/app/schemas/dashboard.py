from datetime import datetime
from pydantic import BaseModel

from app.schemas.drift import DriftEventRead
from app.schemas.health_check import HealthCheckRead


class DeviceStatusSummary(BaseModel):
    device_id: int
    hostname: str
    ip_address: str
    role: str
    site: str
    status: str
    last_check_at: datetime | None
    failed_checks: int
    total_checks: int
    availability_percent: float


class DashboardSummary(BaseModel):
    total_devices: int
    active_devices: int
    healthy: int
    warning: int
    critical: int
    unknown: int
    failed_checks: list[HealthCheckRead]
    recent_drift: list[DriftEventRead]
    devices: list[DeviceStatusSummary]
