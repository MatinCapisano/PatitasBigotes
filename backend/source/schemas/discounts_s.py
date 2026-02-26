from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UpdateDiscountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    type: Literal["percent", "fixed"] | None = None
    value: float | None = Field(default=None, gt=0)
    scope: Literal["all", "category", "product", "product_list"] | None = None
    scope_value: str | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    product_ids: list[int] | None = None


class CreateDiscountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    type: Literal["percent", "fixed"]
    value: float = Field(gt=0)
    scope: Literal["all", "category", "product", "product_list"]
    scope_value: str | None = None
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    product_ids: list[int] = Field(default_factory=list)
