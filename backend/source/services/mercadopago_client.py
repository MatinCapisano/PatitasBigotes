from __future__ import annotations

import time

from sqlalchemy.orm import Session

from source.dependencies.mercadopago_d import (
    _extract_mercadopago_data_id,
    _is_mercadopago_signature_valid,
)
from source.db.config import (
    get_mercadopago_access_token,
    get_mercadopago_timeout_seconds,
)
from source.services.payment_errors import (
    PaymentProviderAuthError,
    PaymentProviderError,
    PaymentProviderTimeoutError,
    PaymentProviderUnavailableError,
    PaymentProviderValidationError,
)

try:
    import mercadopago
except ImportError as exc:  # pragma: no cover - dependency availability
    mercadopago = None
    _import_error = exc
else:
    _import_error = None

MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 0.2


def _get_sdk():
    if mercadopago is None:
        raise PaymentProviderUnavailableError(
            "mercadopago SDK is not installed. Install with: pip install mercadopago"
        ) from _import_error

    return mercadopago.SDK(get_mercadopago_access_token())


def _handle_response_status(status: int, *, operation: str) -> None:
    if status in {400, 404, 422}:
        raise PaymentProviderValidationError(f"mercadopago {operation} rejected")
    if status in {401, 403}:
        raise PaymentProviderAuthError("mercadopago credentials rejected")
    if status >= 400:
        raise PaymentProviderError(f"mercadopago {operation} failed")


def create_checkout_preference(
    preference_payload: dict,
    *,
    idempotency_key: str | None = None,
) -> dict:
    sdk = _get_sdk()
    options = {"timeout": get_mercadopago_timeout_seconds()}
    if idempotency_key:
        options["headers"] = {"x-idempotency-key": idempotency_key}
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            response = sdk.preference().create(preference_payload, options)
        except TimeoutError as exc:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderTimeoutError(
                    "mercadopago request timed out"
                ) from exc
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue
        except Exception as exc:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderUnavailableError(
                    "mercadopago request failed"
                ) from exc
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue

        status = int(response.get("status", 0))
        data = response.get("response")
        if status >= 500:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderUnavailableError("mercadopago unavailable")
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue
        _handle_response_status(status, operation="preference creation")
        if not isinstance(data, dict):
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderUnavailableError(
                    "mercadopago invalid response payload"
                )
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue

        preference_id = data.get("id")
        init_point = data.get("init_point")
        sandbox_init_point = data.get("sandbox_init_point")
        if not preference_id:
            raise PaymentProviderValidationError("mercadopago preference id missing")
        if not init_point and not sandbox_init_point:
            raise PaymentProviderValidationError("mercadopago checkout url missing")

        return data

    raise PaymentProviderUnavailableError("mercadopago preference creation failed")


def get_payment_by_id(payment_id: str | int) -> dict:
    sdk = _get_sdk()
    payment_id_str = str(payment_id).strip()
    if not payment_id_str:
        raise PaymentProviderValidationError("mercadopago payment id is required")

    options = {"timeout": get_mercadopago_timeout_seconds()}
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            response = sdk.payment().get(payment_id_str, options)
        except TimeoutError as exc:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderTimeoutError(
                    "mercadopago request timed out"
                ) from exc
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue
        except Exception as exc:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderUnavailableError(
                    "mercadopago request failed"
                ) from exc
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue

        status = int(response.get("status", 0))
        data = response.get("response")
        if status >= 500:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderUnavailableError("mercadopago unavailable")
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue

        _handle_response_status(status, operation="payment lookup")
        if not isinstance(data, dict):
            if attempt == MAX_RETRY_ATTEMPTS:
                raise PaymentProviderUnavailableError(
                    "mercadopago invalid response payload"
                )
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
            continue
        return data

    raise PaymentProviderUnavailableError("mercadopago payment lookup failed")


def resolver_evento_webhook_mercadopago(
    *,
    payload: dict,
    x_signature: str | None,
    x_request_id: str | None,
    db: Session,
) -> dict:
    if not isinstance(payload, dict):
        return {"processed": False, "reason": "invalid webhook payload"}

    data_id = _extract_mercadopago_data_id(payload)
    if data_id is None:
        return {"processed": False, "reason": "missing data.id"}

    is_signature_valid = _is_mercadopago_signature_valid(
        data_id=data_id,
        request_id=x_request_id,
        signature_header=x_signature,
    )
    if not is_signature_valid:
        return {"processed": False, "reason": "invalid signature"}

    try:
        mp_payment = get_payment_by_id(data_id)
    except Exception:
        return {"processed": False, "reason": "payment lookup failed"}

    # Local imports avoid a module cycle: payment_s imports this client module.
    from source.services.payment_s import (
        apply_mercadopago_normalized_state,
        find_payment_for_mercadopago_event,
        normalize_mp_payment_state,
    )

    try:
        normalized_state = normalize_mp_payment_state(mp_payment)
    except Exception:
        return {"processed": False, "reason": "invalid mercadopago payment payload"}

    external_ref = str(normalized_state["external_reference"])
    try:
        payment = find_payment_for_mercadopago_event(
            preference_id=None,
            external_ref=external_ref,
            db=db,
        )
    except Exception:
        return {"processed": False, "reason": "reconciliation failed"}

    if payment is None:
        return {"processed": False, "reason": "payment not found"}

    try:
        updated_payment = apply_mercadopago_normalized_state(
            payment_id=int(payment["id"]),
            normalized_state=normalized_state,
            notification_payload=payload,
            db=db,
        )
    except Exception as exc:
        return {"processed": False, "reason": str(exc)}

    return {"processed": True, "payment": updated_payment}
