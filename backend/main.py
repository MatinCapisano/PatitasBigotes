from datetime import datetime
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from auth.security import decode_access_token
from source.services.discount_s import (
    delete_discount,
    list_discounts,
    update_discount,
)
from source.services.orders_s import (
    add_item_to_draft_order,
    change_order_status,
    get_or_create_draft_order,
    get_order_for_user,
    pay_order,
    remove_item_from_draft_order,
)
from source.services.products_s import filter_and_sort_products, get_product_by_id

app = FastAPI(
    title="Sales API",
    version="0.1.0",
    description="API para página de ventas. Etapa inicial."
)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject",
        )

    return payload


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required",
        )

    return current_user


class AddOrderItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class UpdateOrderStatusRequest(BaseModel):
    status: Literal["draft", "submitted", "paid", "cancelled"]


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str
    last_name: str
    email: EmailStr
    password: str


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


class PayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_ref: str
    paid_amount: float = Field(gt=0)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# -------------------------
# PRODUCTS
# -------------------------

PRODUCTS = [
    {"id": 1, "name": "Laptop", "price": 1200, "category": "electronics"},
    {"id": 2, "name": "Mouse", "price": 25, "category": "electronics"},
    {"id": 3, "name": "Chair", "price": 80, "category": "furniture"},
]

@app.get("/products")
def get_products(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: Optional[Literal["price", "name"]] = Query(None),
    sort_order: Literal["asc", "desc"] = Query("asc"),
):
    products = filter_and_sort_products(
        min_price=min_price,
        max_price=max_price,
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return {
        "data": products,
        "meta": {
            "filters": {
                "min_price": min_price,
                "max_price": max_price,
                "category": category,
                "sort_by": sort_by,
                "sort_order": sort_order,
            }
        }
    }

@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = get_product_by_id(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "data": product
    }


@app.post("/products")
def create_product(_: dict = Depends(require_admin)):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }


@app.put("/products/{product_id}")
def update_product(product_id: int, _: dict = Depends(require_admin)):
    return {
        "data": {
            "id": product_id,
            "status": "updated"
        }
    }


@app.patch("/products/{product_id}")
def patch_product(product_id: int, _: dict = Depends(require_admin)):
    return {
        "data": {
            "id": product_id,
            "status": "patched"
        }
    }


@app.delete("/products/{product_id}")
def delete_product(product_id: int, _: dict = Depends(require_admin)):
    return {
        "data": {
            "id": product_id,
            "status": "deleted"
        }
    }


# -------------------------
# USERS
# -------------------------

@app.post("/users")
def create_user(payload: CreateUserRequest):
    user_data = payload.model_dump()
    return {
        "data": {
            "id": 1,
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["email"],
            "is_admin": False,
            "is_active": True,
            "status": "created",
        }
    }


# -------------------------
# ORDERS
# -------------------------

@app.get("/orders/draft")
def get_or_create_draft(current_user: dict = Depends(get_current_user)):
    user_ref = str(current_user["sub"])
    order, created = get_or_create_draft_order(user_ref)
    return {
        "data": order,
        "meta": {
            "created": created,
        },
    }


@app.post("/orders/draft/items")
def add_item_to_draft(
    payload: AddOrderItemRequest,
    current_user: dict = Depends(get_current_user),
):
    user_ref = str(current_user["sub"])
    product = get_product_by_id(payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        order = add_item_to_draft_order(
            user_ref=user_ref,
            product=product,
            quantity=payload.quantity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"data": order}


@app.delete("/orders/draft/items/{item_id}")
def remove_item_from_draft(
    item_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_ref = str(current_user["sub"])
    try:
        order = remove_item_from_draft_order(user_ref=user_ref, item_id=item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if order is None:
        raise HTTPException(status_code=404, detail="Draft order item not found")

    return {"data": order}


@app.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: UpdateOrderStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    user_ref = str(current_user["sub"])
    current_order = get_order_for_user(user_ref=user_ref, order_id=order_id)
    if current_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_order["status"] != "draft":
        raise HTTPException(
            status_code=400,
            detail="Order can only be modified in draft status",
        )

    try:
        order = change_order_status(
            user_ref=user_ref,
            order_id=order_id,
            new_status=payload.status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"data": order}


@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_ref = str(current_user["sub"])
    order = get_order_for_user(user_ref=user_ref, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"data": order}


@app.post("/orders/{order_id}/pay")
def pay_order_endpoint(
    order_id: int,
    payload: PayOrderRequest,
    current_user: dict = Depends(get_current_user),
):
    payment_ref = payload.payment_ref.strip()
    if not payment_ref:
        raise HTTPException(status_code=400, detail="payment_ref is required")

    user_ref = str(current_user["sub"])
    try:
        order = pay_order(
            user_ref=user_ref,
            order_id=order_id,
            payment_ref=payment_ref,
            paid_amount=payload.paid_amount,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"data": order}


# -------------------------
# DISCOUNTS
# -------------------------

@app.get("/discounts")
def get_discounts(_: dict = Depends(require_admin)):
    return {"data": list_discounts()}


@app.patch("/discounts/{discount_id}")
def patch_discount(
    discount_id: int,
    payload: UpdateDiscountRequest,
    _: dict = Depends(require_admin),
):
    updates = payload.model_dump(exclude_none=True)
    try:
        discount = update_discount(discount_id=discount_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if discount is None:
        raise HTTPException(status_code=404, detail="discount not found")

    return {"data": discount}


@app.delete("/discounts/{discount_id}")
def remove_discount(discount_id: int, _: dict = Depends(require_admin)):
    discount = delete_discount(discount_id=discount_id)
    if discount is None:
        raise HTTPException(status_code=404, detail="discount not found")
    return {"data": discount}


# -------------------------
# TURNS
# -------------------------

@app.post("/turns")
def create_turn(_: dict = Depends(require_admin)):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }
