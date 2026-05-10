from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re


SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.@:-]{1,120}$")


class RunbookRead(BaseModel):
    id: str
    name: str
    description: str
    action_type: str
    commands: list[str]


class AutomationRunRead(BaseModel):
    id: int
    device_id: int
    runbook_id: str
    action_type: str
    command_id: str
    command: str
    status: str
    exit_code: int | None
    stdout: str
    stderr: str
    requested_by: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None

    model_config = ConfigDict(from_attributes=True)


class AutomationRunList(BaseModel):
    items: list[AutomationRunRead]
    total: int


class AutomationRunbookResult(BaseModel):
    device_id: int
    hostname: str
    runbook_id: str
    status: str
    runs: list[AutomationRunRead]


class TriageResult(BaseModel):
    status: str
    checked_devices: int
    affected_devices: int
    incidents_opened: int
    incidents_resolved: int
    automation_results: list[AutomationRunbookResult]
    notification_sent: bool


class AutomationRequest(BaseModel):
    ssh_username: str | None = Field(default=None, max_length=120)

    @field_validator("ssh_username")
    @classmethod
    def validate_ssh_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not SAFE_NAME_RE.match(value):
            raise ValueError("ssh_username contains unsupported characters")
        return value


class RestartServiceRequest(AutomationRequest):
    service_name: str = Field(..., max_length=120)

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, value: str) -> str:
        if not SAFE_NAME_RE.match(value):
            raise ValueError("service_name contains unsupported characters")
        return value


class RestartContainerRequest(AutomationRequest):
    container_name: str = Field(..., max_length=120)

    @field_validator("container_name")
    @classmethod
    def validate_container_name(cls, value: str) -> str:
        if not SAFE_NAME_RE.match(value):
            raise ValueError("container_name contains unsupported characters")
        return value
