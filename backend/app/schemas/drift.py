from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DriftEventRead(BaseModel):
    id: int
    device_id: int
    event_type: str
    severity: str
    title: str
    description: str
    previous_value: str | None
    current_value: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriftEventList(BaseModel):
    items: list[DriftEventRead]
    total: int
