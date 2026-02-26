from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["bank_transfer", "mercadopago"]
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    expires_in_minutes: int = Field(default=60, gt=0, le=1440)
