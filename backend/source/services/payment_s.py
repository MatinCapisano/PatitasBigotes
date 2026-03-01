from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
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
from source.db.models import Order, Payment, WebhookEvent
from source.services.mercadopago_client import create_checkout_preference
from source.services.stock_reservations_s import (
    consume_reservations_for_paid_order,
    expire_active_reservations,
    list_active_reservations_for_order,
    release_reservations_for_cancelled_order,
)

ALLOWED_PAYMENT_METHODS = {"bank_transfer", "mercadopago"}
MERCADOPAGO_PROVIDER_TO_INTERNAL_STATUS = {
    "approved": "paid",
    "accredited": "paid",
    "pending": "pending",
    "in_process": "pending",
    "in_mediation": "pending",
    "authorized": "pending",
    "rejected": "cancelled",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "expired": "expired",
}
ALLOWED_PAYMENT_TRANSITIONS = {
    "pending": {"pending", "paid", "cancelled", "expired"},
    "paid": {"paid"},
    "cancelled": {"cancelled"},
    "expired": {"expired"},
}

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


def _normalize_webhook_key_part(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


def acquire_webhook_event(
    *,
    provider: str,
    event_key: str,
    payload: dict | None,
    db: Session,
) -> bool:
    normalized_provider = _normalize_webhook_key_part(provider)
    normalized_key = _normalize_webhook_key_part(event_key)
    if normalized_provider is None:
        raise ValueError("provider is required")
    if normalized_key is None:
        raise ValueError("event_key is required")

    now = datetime.utcnow()
    event = WebhookEvent(
        provider=normalized_provider,
        event_key=normalized_key,
        status="processing",
        payload=_serialize_provider_payload(payload) if isinstance(payload, dict) else None,
        received_at=now,
        processed_at=None,
        last_error=None,
    )
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
        return True
    except IntegrityError:
        existing = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.provider == normalized_provider,
                WebhookEvent.event_key == normalized_key,
            )
            .with_for_update()
            .first()
        )
        if existing is None:
            return False
        if existing.status == "failed":
            existing.status = "processing"
            existing.received_at = now
            existing.processed_at = None
            existing.last_error = None
            if isinstance(payload, dict):
                existing.payload = _serialize_provider_payload(payload)
            db.flush()
            return True
        return False


def mark_webhook_event_processed(
    *,
    provider: str,
    event_key: str,
    db: Session,
) -> None:
    event = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.provider == provider,
            WebhookEvent.event_key == event_key,
        )
        .first()
    )
    if event is None:
        return
    event.status = "processed"
    event.processed_at = datetime.utcnow()
    event.last_error = None
    db.flush()


def mark_webhook_event_failed(
    *,
    provider: str,
    event_key: str,
    error_message: str,
    db: Session,
) -> None:
    event = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.provider == provider,
            WebhookEvent.event_key == event_key,
        )
        .first()
    )
    if event is None:
        return
    event.status = "failed"
    event.processed_at = datetime.utcnow()
    event.last_error = (error_message or "webhook processing failed")[:2000]
    db.flush()


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _require_normalized_str(value: object, *, field: str, lower: bool = False) -> str:
    if value is None:
        raise ValueError(f"missing mercadopago {field}")
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"missing mercadopago {field}")
    if lower:
        return normalized.lower()
    return normalized


def _to_float_or_none(value: object, *, field: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid mercadopago {field}") from None


def normalize_mp_payment_state(mp_payment: dict) -> dict:
    if not isinstance(mp_payment, dict):
        raise ValueError("invalid mercadopago payment payload")

    provider_payment_id = _require_normalized_str(mp_payment.get("id"), field="id")
    provider_status = _require_normalized_str(
        mp_payment.get("status"), field="status", lower=True
    )
    external_reference = _require_normalized_str(
        mp_payment.get("external_reference"),
        field="external_reference",
    )
    internal_status = _map_mercadopago_provider_status(provider_status)

    raw_currency = mp_payment.get("currency_id")
    currency = None
    if raw_currency is not None:
        currency = str(raw_currency).strip().upper() or None

    amount = _to_float_or_none(
        mp_payment.get("transaction_amount"),
        field="transaction_amount",
    )
    payer = mp_payment.get("payer")
    payer_data = payer if isinstance(payer, dict) else {}
    transaction_details = mp_payment.get("transaction_details")
    normalized_transaction_details = (
        transaction_details if isinstance(transaction_details, dict) else {}
    )

    return {
        "provider_payment_id": provider_payment_id,
        "provider_status": provider_status,
        "provider_status_detail": mp_payment.get("status_detail"),
        "internal_status": internal_status,
        "external_reference": external_reference,
        "amount": amount,
        "currency": currency,
        "date_created": mp_payment.get("date_created"),
        "date_approved": mp_payment.get("date_approved"),
        "date_last_updated": mp_payment.get("date_last_updated"),
        "payment_method_id": mp_payment.get("payment_method_id"),
        "payment_type_id": mp_payment.get("payment_type_id"),
        "payer_id": payer_data.get("id"),
        "payer_email": payer_data.get("email"),
        "metadata": (
            mp_payment.get("metadata")
            if isinstance(mp_payment.get("metadata"), dict)
            else {}
        ),
        "additional_info": (
            mp_payment.get("additional_info")
            if isinstance(mp_payment.get("additional_info"), dict)
            else {}
        ),
        "transaction_details": normalized_transaction_details,
        "raw": mp_payment,
    }


def _get_checkout_payload(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    checkout = payload.get("checkout")
    if not isinstance(checkout, dict):
        return None
    return checkout


def _get_checkout_preference_id(payload: dict | None) -> str | None:
    checkout = _get_checkout_payload(payload)
    if checkout is None:
        return None
    return _normalize_optional_str(checkout.get("preference_id"))


def _get_checkout_external_ref(payload: dict | None) -> str | None:
    checkout = _get_checkout_payload(payload)
    if checkout is None:
        return None
    return _normalize_optional_str(checkout.get("external_ref"))


def _has_checkout_preference(payload: dict | None) -> bool:
    return _get_checkout_preference_id(payload) is not None


def _map_mercadopago_provider_status(provider_status: str) -> str:
    normalized_status = provider_status.strip().lower()
    if not normalized_status:
        raise ValueError("provider_status is required")
    mapped = MERCADOPAGO_PROVIDER_TO_INTERNAL_STATUS.get(normalized_status)
    if mapped is None:
        raise ValueError("unsupported mercadopago provider_status")
    return mapped


def _assert_valid_payment_transition(current_status: str, next_status: str) -> None:
    allowed = ALLOWED_PAYMENT_TRANSITIONS.get(current_status, {current_status})
    if next_status not in allowed:
        raise ValueError("invalid payment status transition")


def _payment_has_preference_id(payment: Payment, preference_id: str) -> bool:
    payload = _deserialize_provider_payload(payment.provider_payload)
    return _get_checkout_preference_id(payload) == preference_id


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


def find_payment_for_mercadopago_event(
    *,
    preference_id: str | None,
    external_ref: str | None,
    db: Session,
) -> dict | None:
    normalized_preference_id = _normalize_optional_str(preference_id)
    normalized_external_ref = _normalize_optional_str(external_ref)
    if normalized_preference_id is None and normalized_external_ref is None:
        raise ValueError("preference_id or external_ref is required")

    if normalized_preference_id is not None:
        candidates = (
            db.query(Payment)
            .filter(
                Payment.method == "mercadopago",
                Payment.provider_payload.isnot(None),
            )
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .all()
        )
        for candidate in candidates:
            if _payment_has_preference_id(candidate, normalized_preference_id):
                return _payment_to_dict(candidate)

    if normalized_external_ref is not None:
        payment = (
            db.query(Payment)
            .filter(
                Payment.method == "mercadopago",
                Payment.external_ref == normalized_external_ref,
            )
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .first()
        )
        if payment is not None:
            return _payment_to_dict(payment)

    return None


def apply_mercadopago_normalized_state(
    *,
    payment_id: int,
    normalized_state: dict,
    notification_payload: dict | None = None,
    db: Session,
) -> dict:
    expire_active_reservations(now=datetime.utcnow(), db=db)

    if not isinstance(normalized_state, dict):
        raise ValueError("normalized_state is required")

    provider_status = _normalize_optional_str(normalized_state.get("provider_status"))
    if provider_status is None:
        raise ValueError("normalized_state.provider_status is required")
    internal_status = _normalize_optional_str(normalized_state.get("internal_status"))
    if internal_status is None:
        raise ValueError("normalized_state.internal_status is required")
    external_reference = _normalize_optional_str(normalized_state.get("external_reference"))
    if external_reference is None:
        raise ValueError("normalized_state.external_reference is required")

    normalized_amount = _to_float_or_none(
        normalized_state.get("amount"),
        field="transaction_amount",
    )
    normalized_currency = _normalize_optional_str(normalized_state.get("currency"))
    if normalized_currency is not None:
        normalized_currency = normalized_currency.upper()

    now = datetime.utcnow()
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.method == "mercadopago")
        .first()
    )
    if payment is None:
        raise LookupError("payment not found")
    order = payment.order
    if order is None:
        raise LookupError("order not found")

    payment_external_ref = _normalize_optional_str(payment.external_ref)
    if payment_external_ref != external_reference:
        raise ValueError("external_reference does not match payment")

    if normalized_amount is not None and abs(float(payment.amount) - normalized_amount) > 0.01:
        raise ValueError("payment amount mismatch")
    if normalized_currency is not None and payment.currency.strip().upper() != normalized_currency:
        raise ValueError("payment currency mismatch")

    _assert_valid_payment_transition(payment.status, internal_status)
    payment.provider_status = provider_status

    existing_payload = _deserialize_provider_payload(payment.provider_payload) or {}
    merged_payload = dict(existing_payload)
    if notification_payload is not None:
        merged_payload["last_event"] = notification_payload
    merged_payload["payment_lookup"] = normalized_state.get("raw")
    merged_payload["reconciliation"] = {
        "provider_payment_id": normalized_state.get("provider_payment_id"),
        "external_reference": external_reference,
        "provider_status": provider_status,
        "provider_status_detail": normalized_state.get("provider_status_detail"),
        "internal_status": internal_status,
        "amount_consistent": normalized_amount is None
        or abs(float(payment.amount) - normalized_amount) <= 0.01,
        "currency_consistent": normalized_currency is None
        or payment.currency.strip().upper() == normalized_currency,
        "date_last_updated": normalized_state.get("date_last_updated"),
    }
    payment.provider_payload = _serialize_provider_payload(merged_payload)

    if payment.status != internal_status:
        payment.status = internal_status
        if internal_status == "paid" and payment.paid_at is None:
            payment.paid_at = now

    if internal_status == "paid":
        if order.status not in {"submitted", "paid"}:
            raise ValueError("order can only be paid from submitted status")
        if order.status == "submitted":
            consume_reservations_for_paid_order(order_id=order.id, db=db)
        if order.status != "paid":
            order.status = "paid"
        if order.paid_at is None:
            order.paid_at = now
    elif internal_status == "cancelled":
        if order.status != "paid":
            release_reservations_for_cancelled_order(
                order_id=order.id,
                reason="order_cancelled",
                db=db,
            )
            if order.status != "cancelled":
                order.status = "cancelled"
            if order.cancelled_at is None:
                order.cancelled_at = now

    db.flush()
    db.refresh(payment)
    return _payment_to_dict(payment)


def create_payment_for_order(
    order_id: int,
    method: str,
    db: Session,
    *,
    user_id: int | None = None,
    idempotency_key: str,
    currency: str | None = None,
    expires_in_minutes: int = 60,
) -> dict:
    expire_active_reservations(now=datetime.utcnow(), db=db)

    if method not in ALLOWED_PAYMENT_METHODS:
        raise ValueError("invalid payment method")
    if expires_in_minutes <= 0:
        raise ValueError("expires_in_minutes must be greater than 0")
    normalized_key = idempotency_key.strip()
    if not normalized_key:
        raise ValueError("idempotency_key is required")

    existing_payment = (
        db.query(Payment)
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
        db.query(Order)
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
    if not list_active_reservations_for_order(order_id=order.id, db=db):
        raise ValueError("order has no active stock reservations")

    amount = round(float(order.total_amount or 0.0), 2)
    if amount <= 0:
        raise ValueError("order total must be greater than 0")

    now = datetime.utcnow()
    active_pending_payment = _find_active_pending_payment(
        db,
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

    try:
        with db.begin_nested():
            db.add(payment)
            db.flush()
    except IntegrityError:
        payment_by_key = (
            db.query(Payment)
            .options(joinedload(Payment.order))
            .filter(Payment.idempotency_key == normalized_key)
            .first()
        )
        if payment_by_key is not None:
            if user_id is not None and int(payment_by_key.order.user_id) != int(user_id):
                raise LookupError("order not found")
            return _payment_to_dict(payment_by_key)

        existing_pending = _find_active_pending_payment(
            db,
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
            checkout_external_ref = _get_checkout_external_ref(
                existing_provider_payload
            )
            if checkout_external_ref is not None and payment.external_ref is None:
                payment.external_ref = checkout_external_ref
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

    db.flush()
    db.refresh(payment)
    return _payment_to_dict(payment)


def _build_manual_payment_idempotency_key(order_id: int, payment_ref: str) -> str:
    digest = hashlib.sha256(payment_ref.encode("utf-8")).hexdigest()[:16]
    return f"manual-order-{order_id}-{digest}"


def confirm_manual_payment_for_order(
    *,
    order_id: int,
    user_id: int,
    payment_ref: str,
    paid_amount: float,
    db: Session,
) -> dict:
    expire_active_reservations(now=datetime.utcnow(), db=db)

    normalized_ref = payment_ref.strip()
    if not normalized_ref:
        raise ValueError("payment_ref is required")
    if paid_amount <= 0:
        raise ValueError("paid_amount must be greater than 0")

    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.payments),
        )
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )
    if order is None or int(order.user_id) != int(user_id):
        raise LookupError("order not found")

    if order.status == "cancelled":
        raise ValueError("cannot pay a cancelled order")
    if order.status not in {"submitted", "paid"}:
        raise ValueError("order can only be paid from submitted status")
    if not order.items:
        raise ValueError("cannot pay an empty order")

    expected_total = round(float(order.total_amount or 0.0), 2)
    received_total = round(float(paid_amount), 2)
    if expected_total != received_total:
        raise ValueError("paid_amount does not match order total")

    existing_paid_by_ref = (
        db.query(Payment)
        .filter(
            Payment.order_id == order.id,
            Payment.status == "paid",
            Payment.external_ref == normalized_ref,
        )
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .first()
    )
    if order.status == "paid":
        if (
            existing_paid_by_ref is not None
            and round(float(existing_paid_by_ref.amount), 2) == received_total
        ):
            return _payment_to_dict(existing_paid_by_ref)
        raise ValueError("order already paid with a different payment_ref")

    consume_reservations_for_paid_order(order_id=order.id, db=db)

    now = datetime.utcnow()
    payment = existing_paid_by_ref
    if payment is None:
        payment = Payment(
            order_id=order.id,
            method="bank_transfer",
            status="paid",
            amount=received_total,
            currency=order.currency or "ARS",
            idempotency_key=_build_manual_payment_idempotency_key(order.id, normalized_ref),
            external_ref=normalized_ref,
            provider_status="manual_confirmed",
            provider_payload=None,
            receipt_url=None,
            expires_at=None,
            paid_at=now,
        )
        db.add(payment)
    else:
        payment.method = payment.method or "bank_transfer"
        payment.status = "paid"
        payment.amount = received_total
        payment.currency = order.currency or payment.currency or "ARS"
        payment.external_ref = normalized_ref
        payment.provider_status = "manual_confirmed"
        payment.paid_at = now

    payment.provider_payload = _serialize_provider_payload(
        {
            "manual_confirmation": {
                "payment_ref": normalized_ref,
                "confirmed_at": now.isoformat() + "Z",
            }
        }
    )

    order.status = "paid"
    if order.paid_at is None:
        order.paid_at = now

    db.flush()
    db.refresh(payment)
    return _payment_to_dict(payment)


def list_payments_for_order(
    order_id: int,
    user_id: int,
    db: Session,
) -> list[dict]:
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == user_id)
        .first()
    )
    if order is None:
        raise LookupError("order not found")

    payments = (
        db.query(Payment)
        .filter(Payment.order_id == order_id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .all()
    )
    return [_payment_to_dict(payment) for payment in payments]


def get_payment_for_user(
    payment_id: int,
    user_id: int,
    db: Session,
) -> dict:
    payment = (
        db.query(Payment)
        .join(Order, Payment.order_id == Order.id)
        .filter(Payment.id == payment_id, Order.user_id == user_id)
        .first()
    )
    if payment is None:
        raise LookupError("payment not found")

    return _payment_to_dict(payment)
