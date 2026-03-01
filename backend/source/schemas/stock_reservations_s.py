from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReservationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    order_id: int
    order_item_id: int
    variant_id: int
    quantity: int
    status: Literal["active", "consumed", "released", "expired"]
    expires_at: datetime
    consumed_at: datetime | None = None
    released_at: datetime | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ExpireReservationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expired_count: int
