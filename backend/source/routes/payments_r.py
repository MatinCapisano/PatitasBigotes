from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from source.dependencies.auth_d import get_current_user, get_current_user_id
from source.db.session import get_db
from source.errors import raise_http_error_from_exception
from source.services.payment_s import get_payment_for_user

router = APIRouter()


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
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
