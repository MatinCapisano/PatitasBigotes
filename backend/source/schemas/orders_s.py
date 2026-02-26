from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AddOrderItemRequest(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0)


class UpdateOrderStatusRequest(BaseModel):
    status: Literal["draft", "submitted", "paid", "cancelled"]


class PayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_ref: str
    paid_amount: float = Field(gt=0)
