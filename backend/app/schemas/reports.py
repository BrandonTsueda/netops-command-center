from datetime import datetime
from pydantic import BaseModel


class MorningReport(BaseModel):
    generated_at: datetime
    markdown: str
    ai_summary: str | None = None
