from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from source.dependencies.auth_d import get_current_user, get_current_user_id
from source.db.session import get_db
from source.errors import raise_http_error_from_exception
from source.schemas import (
    AddOrderItemRequest,
    CreateOrderPaymentRequest,
    PayOrderRequest,
    UpdateOrderStatusRequest,
)
from source.services.orders_s import (
    add_item_to_draft_order,
    change_order_status,
    get_or_create_draft_order,
    get_order_for_user,
    pay_order,
    remove_item_from_draft_order,
)
from source.services.payment_s import create_payment_for_order, list_payments_for_order
from source.services.products_s import get_variant_by_id

router = APIRouter()


@router.get("/orders/draft")
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


@router.post("/orders/draft/items")
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


@router.delete("/orders/draft/items/{item_id}")
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


@router.patch("/orders/{order_id}/status")
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


@router.get("/orders/{order_id}")
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


@router.post("/orders/{order_id}/pay")
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


@router.post("/orders/{order_id}/payments", status_code=status.HTTP_201_CREATED)
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


@router.get("/orders/{order_id}/payments")
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
