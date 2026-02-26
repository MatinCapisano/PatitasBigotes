import hashlib
import hmac

from source.db.config import get_mercadopago_webhook_secret


def _extract_mercadopago_data_id(payload: dict) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    raw_id = data.get("id")
    if raw_id is None:
        return None
    data_id = str(raw_id).strip()
    if not data_id:
        return None
    return data_id


def _parse_mercadopago_signature_header(
    signature_header: str | None,
) -> tuple[str | None, str | None]:
    if signature_header is None:
        return None, None
    parsed: dict[str, str] = {}
    for item in signature_header.split(","):
        key, _, value = item.strip().partition("=")
        if not key or not value:
            continue
        parsed[key.strip().lower()] = value.strip()
    return parsed.get("ts"), parsed.get("v1")


def _is_mercadopago_signature_valid(
    *,
    data_id: str,
    request_id: str | None,
    signature_header: str | None,
) -> bool:
    normalized_request_id = (request_id or "").strip()
    ts, v1 = _parse_mercadopago_signature_header(signature_header)
    if not normalized_request_id or not ts or not v1:
        return False
    manifest = f"id:{data_id};request-id:{normalized_request_id};ts:{ts};"
    secret = get_mercadopago_webhook_secret()
    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=manifest.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), v1.lower())
