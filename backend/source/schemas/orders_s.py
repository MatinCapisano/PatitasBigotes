from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AddOrderItemRequest(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0)


class UpdateOrderStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["draft", "submitted", "paid", "cancelled"]
    payment_ref: str | None = None
    paid_amount: float | None = Field(default=None, gt=0)


class PayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_ref: str
    paid_amount: float = Field(gt=0)


class ManualOrderCustomerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=6, max_length=30)


class ManualOrderItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variant_id: int
    quantity: int = Field(gt=0)


class CreateManualSubmittedOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer: ManualOrderCustomerRequest
    items: list[ManualOrderItemRequest] = Field(min_length=1)


class PublicGuestCheckoutItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variant_id: int
    quantity: int = Field(gt=0, le=10)


class PublicGuestCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer: ManualOrderCustomerRequest
    items: list[PublicGuestCheckoutItemRequest] = Field(min_length=1, max_length=20)
    website: str | None = Field(default=None, max_length=0)
