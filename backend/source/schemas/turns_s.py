from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime | None = None
    notes: str | None = None
