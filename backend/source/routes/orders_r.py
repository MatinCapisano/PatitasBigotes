from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from source.dependencies.auth_d import get_current_user, get_current_user_id, require_admin
from source.db.session import get_db_transactional
from source.errors import raise_http_error_from_exception
from source.schemas import (
    AddOrderItemRequest,
    CreateManualSubmittedOrderRequest,
    CreateOrderPaymentRequest,
    PayOrderRequest,
    PublicGuestCheckoutRequest,
    UpdateOrderStatusRequest,
)
from source.services.orders_s import (
    add_item_to_draft_order,
    change_order_status,
    create_manual_submitted_order,
    get_order_reservations_for_user,
    get_or_create_draft_order,
    get_order_for_user,
    pay_order,
    remove_item_from_draft_order,
)
from source.services.anti_abuse_s import enforce_public_guest_checkout_limits
from source.services.payment_s import create_payment_for_order, list_payments_for_order

router = APIRouter()


def _client_ip_from_request(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/checkout/guest", status_code=status.HTTP_201_CREATED)
def create_guest_checkout_order(
    payload: PublicGuestCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db_transactional),
):
    try:
        enforce_public_guest_checkout_limits(
            client_ip=_client_ip_from_request(request),
            email=payload.customer.email,
            website=payload.website,
        )
        result = create_manual_submitted_order(
            email=payload.customer.email,
            first_name=payload.customer.first_name,
            last_name=payload.customer.last_name,
            phone=payload.customer.phone,
            items=[item.model_dump() for item in payload.items],
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": result}


@router.post("/orders/manual/submitted")
def create_manual_submitted(
    payload: CreateManualSubmittedOrderRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db_transactional),
):
    try:
        result = create_manual_submitted_order(
            email=payload.customer.email,
            first_name=payload.customer.first_name,
            last_name=payload.customer.last_name,
            phone=payload.customer.phone,
            items=[item.model_dump() for item in payload.items],
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": result}


@router.get("/orders/draft")
def get_or_create_draft(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        order, created = get_or_create_draft_order(user_id=user_id, db=db)
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
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        order = add_item_to_draft_order(
            user_id=user_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": order}


@router.delete("/orders/draft/items/{item_id}")
def remove_item_from_draft(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        order = remove_item_from_draft_order(user_id=user_id, item_id=item_id, db=db)
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
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        order = change_order_status(
            user_id=user_id,
            order_id=order_id,
            new_status=payload.status,
            is_admin=bool(current_user.get("is_admin", False)),
            payment_ref=payload.payment_ref,
            paid_amount=payload.paid_amount,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": order}


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        order = get_order_for_user(user_id=user_id, order_id=order_id, db=db)
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
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        order = pay_order(
            user_id=user_id,
            order_id=order_id,
            payment_ref=payload.payment_ref,
            paid_amount=payload.paid_amount,
            db=db,
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
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)

    try:
        payment = create_payment_for_order(
            order_id=order_id,
            method=payload.method,
            db=db,
            user_id=user_id,
            idempotency_key=idempotency_key,
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
    db: Session = Depends(get_db_transactional),
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


@router.get("/orders/{order_id}/reservations")
def list_order_reservations(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)
    try:
        reservations = get_order_reservations_for_user(
            user_id=user_id,
            order_id=order_id,
            is_admin=bool(current_user.get("is_admin", False)),
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": reservations}
