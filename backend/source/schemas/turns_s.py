from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime | None = None
    notes: str | None = None


class UpdateTurnStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["confirmed", "cancelled"]
