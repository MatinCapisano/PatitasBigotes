from pydantic import BaseModel, ConfigDict


class CreateCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class UpdateCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class PatchCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None


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


class CreateVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int
    sku: str
    size: str | None = None
    color: str | None = None
    price: int
    stock: int = 0
    active: bool = True


class UpdateVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int
    sku: str
    size: str | None = None
    color: str | None = None
    price: int
    stock: int
    active: bool


class PatchVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int | None = None
    sku: str | None = None
    size: str | None = None
    color: str | None = None
    price: int | None = None
    stock: int | None = None
    active: bool | None = None
