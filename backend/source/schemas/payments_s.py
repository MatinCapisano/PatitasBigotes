from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["bank_transfer", "mercadopago"]
    currency: Literal["ARS"] | None = Field(
        default=None,
    )
    expires_in_minutes: int = Field(default=60, gt=0, le=1440)
