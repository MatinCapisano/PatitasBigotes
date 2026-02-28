from pydantic import BaseModel, ConfigDict


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str | None = None
    category: str
    active: bool = True


class UpdateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str | None = None
    category: str
    active: bool


class PatchProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    description: str | None = None
    category: str | None = None
    active: bool | None = None
