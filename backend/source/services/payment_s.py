from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import json

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from source.db.config import (
    get_mercadopago_env,
    get_mercadopago_failure_url,
    get_mercadopago_notification_url,
    get_mercadopago_pending_url,
    get_mercadopago_success_url,
)
from source.db.models import Order, Payment
from source.db.session import SessionLocal
from source.services.mercadopago_client import create_checkout_preference

ALLOWED_PAYMENT_METHODS = {"bank_transfer", "mercadopago"}


@contextmanager
def _session_scope(db: Session | None):
    owns_session = db is None
    session = db or SessionLocal()
    try:
        yield session, owns_session
    finally:
        if owns_session:
            session.close()


def _payment_to_dict(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "method": payment.method,
        "status": payment.status,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "idempotency_key": payment.idempotency_key,
        "external_ref": payment.external_ref,
        "provider_status": payment.provider_status,
        "provider_payload": payment.provider_payload,
        "receipt_url": payment.receipt_url,
        "expires_at": payment.expires_at,
        "paid_at": payment.paid_at,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }


def _serialize_provider_payload(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _deserialize_provider_payload(payload: str | None) -> dict | None:
    if payload is None:
        return None
    try:
        parsed = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _has_checkout_preference(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    checkout = payload.get("checkout")
    if not isinstance(checkout, dict):
        return False
    preference_id = checkout.get("preference_id")
    return isinstance(preference_id, str) and bool(preference_id.strip())


def _find_active_pending_payment(
    session: Session,
    *,
    order_id: int,
    method: str,
    now: datetime,
) -> Payment | None:
    return (
        session.query(Payment)
        .filter(
            Payment.order_id == order_id,
            Payment.method == method,
            Payment.status == "pending",
            or_(Payment.expires_at.is_(None), Payment.expires_at > now),
        )
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .first()
    )


def _validate_active_pending_compatibility(
    active_payment: Payment,
    *,
    requested_amount: float,
    requested_currency: str,
) -> None:
    active_amount = round(float(active_payment.amount), 2)
    if active_amount != round(float(requested_amount), 2):
        raise ValueError(
            "there is already an active pending payment with a different amount"
        )
    if active_payment.currency != requested_currency:
        raise ValueError(
            "there is already an active pending payment with a different currency"
        )


def _build_bank_transfer_payload(
    order_id: int,
    payment_id: int,
    amount: float,
    currency: str,
) -> dict:
    return {
        "instructions": {
            "alias": "patitas.bigotes",
            "bank_name": "Banco Demo",
            "reference": f"ORDER-{order_id}-PAY-{payment_id}",
            "amount": amount,
            "currency": currency,
        }
    }


def _build_mercadopago_payload(
    order_id: int,
    payment_id: int,
    amount: float,
    currency: str,
    expires_at: datetime,
    payment_idempotency_key: str,
) -> tuple[str, dict]:
    external_ref = f"mp-order-{order_id}-pay-{payment_id}"
    provider_idempotency_key = f"mp-preference-{payment_idempotency_key}"
    preference_payload = {
        "external_reference": external_ref,
        "items": [
            {
                "id": str(payment_id),
                "title": f"Order #{order_id}",
                "quantity": 1,
                "currency_id": currency,
                "unit_price": amount,
            }
        ],
        "back_urls": {
            "success": get_mercadopago_success_url(),
            "failure": get_mercadopago_failure_url(),
            "pending": get_mercadopago_pending_url(),
        },
        "notification_url": get_mercadopago_notification_url(),
        "expires": True,
        "date_of_expiration": expires_at.replace(microsecond=0).isoformat() + "Z",
        "metadata": {
            "order_id": order_id,
            "payment_id": payment_id,
            "external_ref": external_ref,
            "currency": currency,
            "amount": amount,
        },
    }
    provider_response = create_checkout_preference(
        preference_payload,
        idempotency_key=provider_idempotency_key,
    )
    env = get_mercadopago_env()
    checkout_url = (
        provider_response.get("sandbox_init_point")
        if env == "sandbox"
        else provider_response.get("init_point")
    )
    if not checkout_url:
        checkout_url = provider_response.get("init_point") or provider_response.get(
            "sandbox_init_point"
        )
    payload = {
        "checkout": {
            "provider": "mercadopago",
            "environment": env,
            "external_ref": external_ref,
            "provider_idempotency_key": provider_idempotency_key,
            "preference_id": provider_response.get("id"),
            "checkout_url": checkout_url,
            "init_point": provider_response.get("init_point"),
            "sandbox_init_point": provider_response.get("sandbox_init_point"),
            "amount": amount,
            "currency": currency,
        }
    }
    return external_ref, payload


def create_payment_for_order(
    order_id: int,
    method: str,
    db: Session | None = None,
    *,
    user_id: int | None = None,
    idempotency_key: str,
    currency: str | None = None,
    expires_in_minutes: int = 60,
) -> dict:
    if method not in ALLOWED_PAYMENT_METHODS:
        raise ValueError("invalid payment method")
    if expires_in_minutes <= 0:
        raise ValueError("expires_in_minutes must be greater than 0")
    normalized_key = idempotency_key.strip()
    if not normalized_key:
        raise ValueError("idempotency_key is required")

    with _session_scope(db) as (session, owns_session):
        existing_payment = (
            session.query(Payment)
            .options(joinedload(Payment.order))
            .filter(Payment.idempotency_key == normalized_key)
            .first()
        )
        if existing_payment is not None:
            if existing_payment.order_id != order_id:
                raise ValueError(
                    "idempotency key already used for a different order"
                )
            if existing_payment.method != method:
                raise ValueError(
                    "idempotency key already used for a different payment method"
                )
            if user_id is not None and int(existing_payment.order.user_id) != int(user_id):
                raise LookupError("order not found")
            return _payment_to_dict(existing_payment)

        order = (
            session.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .with_for_update()
            .first()
        )
        if order is None:
            raise LookupError("order not found")
        if user_id is not None and int(order.user_id) != int(user_id):
            raise LookupError("order not found")
        if order.status == "cancelled":
            raise ValueError("cannot create payment for a cancelled order")
        if order.status != "submitted":
            raise ValueError("payment can only be created for submitted orders")
        if not order.items:
            raise ValueError("cannot create payment for an empty order")

        amount = round(float(order.total_amount or 0.0), 2)
        if amount <= 0:
            raise ValueError("order total must be greater than 0")

        now = datetime.utcnow()
        active_pending_payment = _find_active_pending_payment(
            session,
            order_id=order.id,
            method=method,
            now=now,
        )
        payment_currency = currency or order.currency or "ARS"
        if active_pending_payment is not None:
            _validate_active_pending_compatibility(
                active_pending_payment,
                requested_amount=amount,
                requested_currency=payment_currency,
            )
            return _payment_to_dict(active_pending_payment)

        expires_at = now + timedelta(minutes=expires_in_minutes)
        payment = Payment(
            order_id=order.id,
            method=method,
            status="pending",
            amount=amount,
            currency=payment_currency,
            idempotency_key=normalized_key,
            external_ref=None,
            provider_status=None,
            provider_payload=None,
            receipt_url=None,
            expires_at=expires_at,
            paid_at=None,
        )
        session.add(payment)
        try:
            session.flush()
        except IntegrityError:
            if not owns_session:
                raise

            session.rollback()
            payment_by_key = (
                session.query(Payment)
                .options(joinedload(Payment.order))
                .filter(Payment.idempotency_key == normalized_key)
                .first()
            )
            if payment_by_key is not None:
                if user_id is not None and int(payment_by_key.order.user_id) != int(user_id):
                    raise LookupError("order not found")
                return _payment_to_dict(payment_by_key)

            existing_pending = _find_active_pending_payment(
                session,
                order_id=order.id,
                method=method,
                now=now,
            )
            if existing_pending is not None:
                _validate_active_pending_compatibility(
                    existing_pending,
                    requested_amount=amount,
                    requested_currency=payment_currency,
                )
                return _payment_to_dict(existing_pending)
            raise

        if method == "bank_transfer":
            provider_payload = _build_bank_transfer_payload(
                order_id=order.id,
                payment_id=payment.id,
                amount=amount,
                currency=payment_currency,
            )
            payment.provider_payload = _serialize_provider_payload(provider_payload)
        elif method == "mercadopago":
            existing_provider_payload = _deserialize_provider_payload(
                payment.provider_payload
            )
            if _has_checkout_preference(existing_provider_payload):
                payment.provider_status = payment.provider_status or "preference_created"
            else:
                external_ref, provider_payload = _build_mercadopago_payload(
                    order_id=order.id,
                    payment_id=payment.id,
                    amount=amount,
                    currency=payment_currency,
                    expires_at=expires_at,
                    payment_idempotency_key=normalized_key,
                )
                payment.external_ref = external_ref
                payment.provider_status = "preference_created"
                payment.provider_payload = _serialize_provider_payload(provider_payload)

        session.flush()
        if owns_session:
            session.commit()
        else:
            session.flush()

        session.refresh(payment)
        return _payment_to_dict(payment)


def list_payments_for_order(
    order_id: int,
    user_id: int,
    db: Session | None = None,
) -> list[dict]:
    with _session_scope(db) as (session, _):
        order = (
            session.query(Order)
            .filter(Order.id == order_id, Order.user_id == user_id)
            .first()
        )
        if order is None:
            raise LookupError("order not found")

        payments = (
            session.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .all()
        )
        return [_payment_to_dict(payment) for payment in payments]


def get_payment_for_user(
    payment_id: int,
    user_id: int,
    db: Session | None = None,
) -> dict:
    with _session_scope(db) as (session, _):
        payment = (
            session.query(Payment)
            .join(Order, Payment.order_id == Order.id)
            .filter(Payment.id == payment_id, Order.user_id == user_id)
            .first()
        )
        if payment is None:
            raise LookupError("payment not found")

        return _payment_to_dict(payment)
