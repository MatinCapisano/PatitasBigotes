from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from source.dependencies.auth_d import get_current_user, get_current_user_id, require_admin
from source.db.session import get_db_transactional
from source.errors import raise_http_error_from_exception
from source.services.payment_s import (
    get_payment_for_user,
    get_payment_public_status,
    list_payments_for_admin,
    list_pending_bank_transfer_payments_for_admin,
)

router = APIRouter()


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
):
    user_id = get_current_user_id(current_user)

    try:
        payment = get_payment_for_user(
            payment_id=payment_id,
            user_id=user_id,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": payment}


@router.get("/payments/public/status")
def get_public_payment_status(
    external_ref: str | None = None,
    preference_id: str | None = None,
    db: Session = Depends(get_db_transactional),
):
    try:
        payment = get_payment_public_status(
            external_ref=external_ref,
            preference_id=preference_id,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": payment}


@router.get("/admin/payments/bank-transfer/pending")
def list_pending_bank_transfer_payments(
    limit: int = 100,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db_transactional),
):
    try:
        payments = list_pending_bank_transfer_payments_for_admin(
            db=db,
            limit=limit,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": payments}


@router.get("/admin/payments")
def list_admin_payments(
    status: str | None = None,
    limit: int = 10,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db_transactional),
):
    try:
        rows = list_payments_for_admin(
            status=status,
            limit=limit,
            sort_by=sort_by,
            sort_dir=sort_dir,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": rows}
