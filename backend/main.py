import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from auth.security import decode_access_token
from source.db.config import get_mercadopago_webhook_token
from source.db.session import get_db
from source.services.discount_s import (
    create_discount,
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
from source.services.payment_s import (
    apply_mercadopago_provider_status,
    create_payment_for_order,
    find_payment_for_mercadopago_event,
    get_payment_for_user,
    list_payments_for_order,
)
from source.services.products_s import (
    filter_and_sort_products,
    get_product_by_id,
    get_variant_by_id,
)

app = FastAPI(
    title="Sales API",
    version="0.1.0",
    description="API para página de ventas. Etapa inicial."
)
bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def _raise_http_error_from_exception(exc: Exception, db: Session | None = None) -> None:
    if db is not None and isinstance(exc, (IntegrityError, SQLAlchemyError)):
        db.rollback()

    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, IntegrityError):
        raise HTTPException(
            status_code=409,
            detail="database constraint violation",
        ) from exc
    if isinstance(exc, SQLAlchemyError):
        raise HTTPException(
            status_code=500,
            detail="database error",
        ) from exc

    raise exc


def _extract_mercadopago_event_fields(payload: dict) -> tuple[str | None, str | None, str | None]:
    data = payload.get("data")
    payment_data = payload.get("payment")
    metadata = payload.get("metadata")

    preference_id = (
        payload.get("preference_id")
        or (data.get("preference_id") if isinstance(data, dict) else None)
        or (payment_data.get("preference_id") if isinstance(payment_data, dict) else None)
    )
    external_ref = (
        payload.get("external_reference")
        or payload.get("external_ref")
        or (data.get("external_reference") if isinstance(data, dict) else None)
        or (data.get("external_ref") if isinstance(data, dict) else None)
        or (payment_data.get("external_reference") if isinstance(payment_data, dict) else None)
        or (payment_data.get("external_ref") if isinstance(payment_data, dict) else None)
        or (metadata.get("external_ref") if isinstance(metadata, dict) else None)
    )
    provider_status = (
        payload.get("status")
        or (data.get("status") if isinstance(data, dict) else None)
        or (payment_data.get("status") if isinstance(payment_data, dict) else None)
    )
    return preference_id, external_ref, provider_status


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
    variant_id: int
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


class PayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_ref: str
    paid_amount: float = Field(gt=0)


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
    _db: Session = Depends(get_db),
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
def get_product(
    product_id: int,
    _db: Session = Depends(get_db),
):
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
def create_product(
    _: dict = Depends(require_admin),
    _db: Session = Depends(get_db),
):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    _: dict = Depends(require_admin),
    _db: Session = Depends(get_db),
):
    return {
        "data": {
            "id": product_id,
            "status": "updated"
        }
    }


@app.patch("/products/{product_id}")
def patch_product(
    product_id: int,
    _: dict = Depends(require_admin),
    _db: Session = Depends(get_db),
):
    return {
        "data": {
            "id": product_id,
            "status": "patched"
        }
    }


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    _: dict = Depends(require_admin),
    _db: Session = Depends(get_db),
):
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
def create_user(
    payload: CreateUserRequest,
    _db: Session = Depends(get_db),
):
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
def get_or_create_draft(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_ref = str(current_user["sub"])
    try:
        order, created = get_or_create_draft_order(user_ref)
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)
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
    db: Session = Depends(get_db),
):
    user_ref = str(current_user["sub"])
    variant = get_variant_by_id(payload.variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found")

    try:
        order = add_item_to_draft_order(
            user_ref=user_ref,
            variant=variant,
            quantity=payload.quantity,
        )
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": order}


@app.delete("/orders/draft/items/{item_id}")
def remove_item_from_draft(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_ref = str(current_user["sub"])
    try:
        order = remove_item_from_draft_order(user_ref=user_ref, item_id=item_id)
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    if order is None:
        raise HTTPException(status_code=404, detail="Draft order item not found")

    return {"data": order}


@app.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: UpdateOrderStatusRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
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
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": order}


@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_ref = str(current_user["sub"])
    try:
        order = get_order_for_user(user_ref=user_ref, order_id=order_id)
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"data": order}


@app.post("/orders/{order_id}/pay")
def pay_order_endpoint(
    order_id: int,
    payload: PayOrderRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
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
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": order}


@app.post("/orders/{order_id}/payments", status_code=status.HTTP_201_CREATED)
def create_order_payment(
    order_id: int,
    payload: CreateOrderPaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(current_user["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
    normalized_idempotency_key = idempotency_key.strip()
    if not normalized_idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )

    try:
        payment = create_payment_for_order(
            order_id=order_id,
            method=payload.method,
            db=db,
            user_id=user_id,
            idempotency_key=normalized_idempotency_key,
            currency=payload.currency,
            expires_in_minutes=payload.expires_in_minutes,
        )
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": payment}


@app.get("/orders/{order_id}/payments")
def list_order_payments(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(current_user["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    try:
        payments = list_payments_for_order(
            order_id=order_id,
            user_id=user_id,
            db=db,
        )
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": payments}


@app.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(current_user["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    try:
        payment = get_payment_for_user(
            payment_id=payment_id,
            user_id=user_id,
            db=db,
        )
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": payment}


@app.post("/payments/webhook/mercadopago")
def mercadopago_webhook(
    payload: dict,
    mp_webhook_token: str | None = Header(default=None, alias="X-MP-Webhook-Token"),
    db: Session = Depends(get_db),
):
    expected_token = get_mercadopago_webhook_token()
    received_token = (mp_webhook_token or "").strip()
    if expected_token and received_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook token",
        )

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid webhook payload")

    preference_id, external_ref, provider_status = _extract_mercadopago_event_fields(payload)
    if preference_id is None and external_ref is None:
        logger.info("mercadopago webhook ignored: missing identifiers")
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"data": {"processed": False, "reason": "missing identifiers"}},
        )

    try:
        payment = find_payment_for_mercadopago_event(
            preference_id=preference_id,
            external_ref=external_ref,
            db=db,
        )
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    if payment is None:
        logger.info(
            "mercadopago webhook not matched: preference_id=%s external_ref=%s",
            preference_id,
            external_ref,
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"data": {"processed": False, "reason": "payment not found"}},
        )

    if not isinstance(provider_status, str) or not provider_status.strip():
        logger.info(
            "mercadopago webhook missing status: payment_id=%s preference_id=%s external_ref=%s",
            payment["id"],
            preference_id,
            external_ref,
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"data": {"processed": False, "reason": "missing provider status"}},
        )

    try:
        updated_payment = apply_mercadopago_provider_status(
            payment_id=int(payment["id"]),
            provider_status=provider_status,
            provider_payload=payload,
            db=db,
        )
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    logger.info(
        "mercadopago webhook processed: payment_id=%s preference_id=%s external_ref=%s provider_status=%s",
        updated_payment["id"],
        preference_id,
        external_ref,
        provider_status,
    )
    return {"data": {"processed": True, "payment": updated_payment}}


# -------------------------
# DISCOUNTS
# -------------------------

@app.get("/discounts")
def get_discounts(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return {"data": list_discounts()}
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)


@app.post("/discounts", status_code=status.HTTP_201_CREATED)
def post_discount(
    payload: CreateDiscountRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        discount = create_discount(payload.model_dump())
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    return {"data": discount}


@app.patch("/discounts/{discount_id}")
def patch_discount(
    discount_id: int,
    payload: UpdateDiscountRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_none=True)
    try:
        discount = update_discount(discount_id=discount_id, updates=updates)
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)

    if discount is None:
        raise HTTPException(status_code=404, detail="discount not found")

    return {"data": discount}


@app.delete("/discounts/{discount_id}")
def remove_discount(
    discount_id: int,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        discount = delete_discount(discount_id=discount_id)
    except Exception as exc:
        _raise_http_error_from_exception(exc, db=db)
    if discount is None:
        raise HTTPException(status_code=404, detail="discount not found")
    return {"data": discount}


# -------------------------
# TURNS
# -------------------------

@app.post("/turns")
def create_turn(
    _: dict = Depends(require_admin),
    _db: Session = Depends(get_db),
):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }
