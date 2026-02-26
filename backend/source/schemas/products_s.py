from pydantic import BaseModel, ConfigDict, Field


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    category: str
    active: bool = True
    stock: int = Field(default=0, ge=0)
    size: str | None = None
    color: str | None = None


class UpdateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    category: str
    active: bool = True


class PatchProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    category: str | None = None
    active: bool | None = None
