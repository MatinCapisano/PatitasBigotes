import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from auth.auth_s import (
    authenticate_user,
    issue_token_pair,
    logout_with_refresh_token,
    refresh_with_token,
)
from auth.security import hash_password
from source.dependencies.auth_d import (
    bearer_scheme,
    get_current_user,
    get_current_user_id,
    require_admin,
)
from source.dependencies.mercadopago_d import (
    _extract_mercadopago_data_id,
    _is_mercadopago_signature_valid,
)
from source.db.models import User
from source.db.session import get_db
from source.errors import raise_http_error_from_exception
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
from source.services.mercadopago_client import get_payment_by_id
from source.services.payment_s import (
    apply_mercadopago_normalized_state,
    create_payment_for_order,
    find_payment_for_mercadopago_event,
    get_payment_for_user,
    list_payments_for_order,
    normalize_mp_payment_state,
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
logger = logging.getLogger(__name__)


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


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    db: Session = Depends(get_db),
):
    user_data = payload.model_dump()
    normalized_email = user_data["email"].strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="email is required")

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="email already exists")

    try:
        user = User(
            first_name=user_data["first_name"].strip(),
            last_name=user_data["last_name"].strip(),
            email=normalized_email,
            phone=None,
            password_hash=hash_password(user_data["password"]),
            is_admin=False,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {
        "data": {
            "id": int(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_admin": bool(user.is_admin),
            "is_active": bool(user.is_active),
            "status": "created",
        }
    }


# -------------------------
# AUTH
# -------------------------

@app.post("/auth/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
        user = authenticate_user(
            email=payload.email,
            password=payload.password,
            db=db,
        )
        tokens = issue_token_pair(user=user, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": tokens}


@app.post("/auth/refresh")
def refresh(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        tokens = refresh_with_token(refresh_token=credentials.credentials, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": tokens}


@app.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        logout_with_refresh_token(refresh_token=credentials.credentials, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": {"logged_out": True}}


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
        raise_http_error_from_exception(exc, db=db)
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
        raise_http_error_from_exception(exc, db=db)

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
        raise_http_error_from_exception(exc, db=db)

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
        raise_http_error_from_exception(exc, db=db)

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
        raise_http_error_from_exception(exc, db=db)
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
        raise_http_error_from_exception(exc, db=db)

    return {"data": order}


@app.post("/orders/{order_id}/payments", status_code=status.HTTP_201_CREATED)
def create_order_payment(
    order_id: int,
    payload: CreateOrderPaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(current_user)
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
        raise_http_error_from_exception(exc, db=db)

    return {"data": payment}


@app.get("/orders/{order_id}/payments")
def list_order_payments(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(current_user)

    try:
        payments = list_payments_for_order(
            order_id=order_id,
            user_id=user_id,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": payments}


@app.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(current_user)

    try:
        payment = get_payment_for_user(
            payment_id=payment_id,
            user_id=user_id,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": payment}


@app.post("/payments/webhook/mercadopago")
def mercadopago_webhook(
    payload: dict,
    x_signature: str | None = Header(default=None, alias="x-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
    db: Session = Depends(get_db),
):
    if not isinstance(payload, dict):
        logger.info(
            "event=mp_webhook_ignored reason=invalid_payload request_id=%s",
            x_request_id,
        )
        return {"data": {"processed": False, "reason": "invalid webhook payload"}}

    data_id = _extract_mercadopago_data_id(payload)
    if data_id is None:
        logger.info(
            "event=mp_webhook_ignored reason=missing_data_id request_id=%s",
            x_request_id,
        )
        return {"data": {"processed": False, "reason": "missing data.id"}}

    is_signature_valid = _is_mercadopago_signature_valid(
        data_id=data_id,
        request_id=x_request_id,
        signature_header=x_signature,
    )
    if not is_signature_valid:
        logger.warning(
            "event=mp_signature_failed request_id=%s data_id=%s",
            x_request_id,
            data_id,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    try:
        mp_payment = get_payment_by_id(data_id)
    except Exception as exc:
        logger.error(
            "event=mp_payment_lookup_failed request_id=%s data_id=%s error=%s",
            x_request_id,
            data_id,
            str(exc),
        )
        return {"data": {"processed": False, "reason": "payment lookup failed"}}

    try:
        normalized_state = normalize_mp_payment_state(mp_payment)
    except Exception as exc:
        logger.info(
            "event=mp_webhook_ignored reason=invalid_mp_payment request_id=%s data_id=%s error=%s",
            x_request_id,
            data_id,
            str(exc),
        )
        return {"data": {"processed": False, "reason": "invalid mercadopago payment payload"}}

    external_ref = str(normalized_state["external_reference"])

    try:
        payment = find_payment_for_mercadopago_event(
            preference_id=None,
            external_ref=external_ref,
            db=db,
        )
    except Exception as exc:
        logger.error(
            "event=mp_reconciliation_failed request_id=%s data_id=%s external_reference=%s error=%s",
            x_request_id,
            data_id,
            external_ref,
            str(exc),
        )
        return {"data": {"processed": False, "reason": "reconciliation failed"}}

    if payment is None:
        logger.info(
            "event=mp_payment_unmatched request_id=%s data_id=%s external_reference=%s",
            x_request_id,
            data_id,
            external_ref,
        )
        return {"data": {"processed": False, "reason": "payment not found"}}

    try:
        updated_payment = apply_mercadopago_normalized_state(
            payment_id=int(payment["id"]),
            normalized_state=normalized_state,
            notification_payload=payload,
            db=db,
        )
    except Exception as exc:
        logger.error(
            "event=mp_payment_update_failed request_id=%s data_id=%s external_reference=%s payment_id=%s mp_status=%s error=%s",
            x_request_id,
            data_id,
            external_ref,
            payment["id"],
            normalized_state.get("provider_status"),
            str(exc),
        )
        return {"data": {"processed": False, "reason": str(exc)}}

    logger.info(
        "event=mp_webhook_processed request_id=%s data_id=%s external_reference=%s payment_id=%s order_id=%s mp_status=%s mp_status_detail=%s processed=%s",
        x_request_id,
        data_id,
        external_ref,
        updated_payment["id"],
        updated_payment["order_id"],
        normalized_state.get("provider_status"),
        normalized_state.get("provider_status_detail"),
        True,
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
        raise_http_error_from_exception(exc, db=db)


@app.post("/discounts", status_code=status.HTTP_201_CREATED)
def post_discount(
    payload: CreateDiscountRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        discount = create_discount(payload.model_dump())
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

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
        raise_http_error_from_exception(exc, db=db)

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
        raise_http_error_from_exception(exc, db=db)
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
