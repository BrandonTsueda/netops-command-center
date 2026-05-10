from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class HealthCheckCreate(BaseModel):
    device_id: int = Field(..., gt=0)
    check_type: str = Field(..., min_length=2, max_length=40, examples=["ping"])
    target: str = Field(..., min_length=1, max_length=300, examples=["192.168.68.1"])
    status: str = Field(..., pattern="^(healthy|warning|critical|unknown)$")
    latency_ms: int | None = Field(default=None, ge=0)
    message: str = Field(default="", max_length=2000)
    observed_value: str | None = Field(default=None, max_length=4000)
    run_id: str | None = Field(default=None, max_length=64)


class HealthCheckRead(HealthCheckCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthCheckList(BaseModel):
    items: list[HealthCheckRead]
    total: int


class DeviceCheckRun(BaseModel):
    device_id: int
    hostname: str
    overall_status: str = Field(..., pattern="^(healthy|warning|critical|unknown)$")
    run_id: str
    results: list[HealthCheckRead]


class FleetCheckRun(BaseModel):
    run_id: str
    checked_devices: int
    healthy: int
    warning: int
    critical: int
    unknown: int
    results: list[DeviceCheckRun]
