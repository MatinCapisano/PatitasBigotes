import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from source.dependencies.mercadopago_d import (
    _extract_mercadopago_data_id,
    _is_mercadopago_signature_valid,
)
from source.db.session import get_db
from source.services.mercadopago_client import get_payment_by_id
from source.services.payment_s import (
    apply_mercadopago_normalized_state,
    find_payment_for_mercadopago_event,
    normalize_mp_payment_state,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/payments/webhook/mercadopago")
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature",
        )

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
