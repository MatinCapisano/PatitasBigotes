import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from source.db.session import get_db_transactional
from source.services.mercadopago_client import resolver_evento_webhook_mercadopago

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/payments/webhook/mercadopago")
def mercadopago_webhook(
    payload: dict,
    x_signature: str | None = Header(default=None, alias="x-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
    db: Session = Depends(get_db_transactional),
):
    result = resolver_evento_webhook_mercadopago(
        payload=payload,
        x_signature=x_signature,
        x_request_id=x_request_id,
        db=db,
    )
    if not result.get("processed") and result.get("reason") == "invalid signature":
        logger.warning(
            "event=mp_signature_failed request_id=%s",
            x_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature",
        )

    logger.info(
        "event=mp_webhook_processed request_id=%s processed=%s reason=%s",
        x_request_id,
        bool(result.get("processed")),
        result.get("reason"),
    )
    return {"data": result}
