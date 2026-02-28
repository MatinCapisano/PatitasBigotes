import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from source.db.session import get_db_transactional
from source.services.mercadopago_client import (
    WebhookInvalidSignatureError,
    WebhookNoOpError,
    resolver_evento_webhook_mercadopago,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/payments/webhook/mercadopago")
def mercadopago_webhook(
    payload: dict,
    x_signature: str | None = Header(default=None, alias="x-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
    db: Session = Depends(get_db_transactional),
):
    try:
        result = resolver_evento_webhook_mercadopago(
            payload=payload,
            x_signature=x_signature,
            x_request_id=x_request_id,
            db=db,
        )
    except WebhookInvalidSignatureError:
        logger.warning(
            "event=mp_signature_failed request_id=%s",
            x_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature",
        )
    except WebhookNoOpError as exc:
        logger.info(
            "event=mp_webhook_noop request_id=%s reason=%s",
            x_request_id,
            str(exc),
        )
        return {"data": {"processed": False, "reason": str(exc)}}
    except Exception:
        logger.exception("event=mp_webhook_error request_id=%s", x_request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="mercadopago webhook processing failed",
        )

    logger.info(
        "event=mp_webhook_processed request_id=%s processed=%s",
        x_request_id,
        bool(result.processed),
    )
    return {
        "data": {
            "processed": bool(result.processed),
            "payment": result.payment,
        }
    }
