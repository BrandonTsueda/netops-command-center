from datetime import datetime
from pydantic import BaseModel, ConfigDict


class IncidentRead(BaseModel):
    id: int
    device_id: int
    severity: str
    title: str
    description: str
    status: str
    opened_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class IncidentList(BaseModel):
    items: list[IncidentRead]
    total: int
