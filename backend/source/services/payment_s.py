from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from source.db.models import Order, Payment
from source.db.session import SessionLocal

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
) -> tuple[str, dict]:
    external_ref = f"mp-order-{order_id}-pay-{payment_id}"
    payload = {
        "checkout": {
            "provider": "mercadopago",
            "external_ref": external_ref,
            "checkout_url": f"https://www.mercadopago.com/checkout/v1/redirect?pref_id={external_ref}",
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
    currency: str | None = None,
    expires_in_minutes: int = 60,
) -> dict:
    if method not in ALLOWED_PAYMENT_METHODS:
        raise ValueError("invalid payment method")
    if expires_in_minutes <= 0:
        raise ValueError("expires_in_minutes must be greater than 0")

    with _session_scope(db) as (session, owns_session):
        order = (
            session.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
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
        payment_currency = currency or order.currency or "ARS"
        payment = Payment(
            order_id=order.id,
            method=method,
            status="pending",
            amount=amount,
            currency=payment_currency,
            idempotency_key=str(uuid4()),
            external_ref=None,
            provider_status=None,
            provider_payload=None,
            receipt_url=None,
            expires_at=now + timedelta(minutes=expires_in_minutes),
            paid_at=None,
        )
        session.add(payment)
        session.flush()

        if method == "bank_transfer":
            provider_payload = _build_bank_transfer_payload(
                order_id=order.id,
                payment_id=payment.id,
                amount=amount,
                currency=payment_currency,
            )
            payment.provider_payload = _serialize_provider_payload(provider_payload)
        elif method == "mercadopago":
            external_ref, provider_payload = _build_mercadopago_payload(
                order_id=order.id,
                payment_id=payment.id,
                amount=amount,
                currency=payment_currency,
            )
            payment.external_ref = external_ref
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
