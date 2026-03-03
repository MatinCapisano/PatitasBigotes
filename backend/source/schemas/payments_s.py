from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["bank_transfer", "mercadopago"]
    currency: Literal["ARS"] | None = Field(
        default=None,
    )
    expires_in_minutes: int = Field(default=60, gt=0, le=1440)


class AdminWebhookReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_key: str = Field(min_length=1, max_length=255)


class SubmitBankTransferReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt_url: str = Field(min_length=5, max_length=1000)
