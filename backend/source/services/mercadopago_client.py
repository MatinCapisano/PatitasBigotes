from __future__ import annotations

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


def _get_sdk():
    if mercadopago is None:
        raise PaymentProviderUnavailableError(
            "mercadopago SDK is not installed. Install with: pip install mercadopago"
        ) from _import_error

    return mercadopago.SDK(get_mercadopago_access_token())


def create_checkout_preference(preference_payload: dict) -> dict:
    sdk = _get_sdk()
    options = {"timeout": get_mercadopago_timeout_seconds()}
    try:
        response = sdk.preference().create(preference_payload, options)
    except TimeoutError as exc:
        raise PaymentProviderTimeoutError("mercadopago request timed out") from exc
    except Exception as exc:
        raise PaymentProviderUnavailableError("mercadopago request failed") from exc

    status = int(response.get("status", 0))
    data = response.get("response")
    if status in {400, 422}:
        raise PaymentProviderValidationError("mercadopago preference rejected")
    if status in {401, 403}:
        raise PaymentProviderAuthError("mercadopago credentials rejected")
    if status >= 500:
        raise PaymentProviderUnavailableError("mercadopago unavailable")
    if status >= 400:
        raise PaymentProviderError("mercadopago preference creation failed")
    if not isinstance(data, dict):
        raise PaymentProviderUnavailableError("mercadopago invalid response payload")

    preference_id = data.get("id")
    init_point = data.get("init_point")
    sandbox_init_point = data.get("sandbox_init_point")
    if not preference_id:
        raise PaymentProviderValidationError("mercadopago preference id missing")
    if not init_point and not sandbox_init_point:
        raise PaymentProviderValidationError("mercadopago checkout url missing")

    return data
