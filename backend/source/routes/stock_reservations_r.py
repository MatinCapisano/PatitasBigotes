from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from source.dependencies.auth_d import require_admin
from source.db.session import get_db_transactional
from source.errors import raise_http_error_from_exception
from source.services.stock_reservations_s import expire_active_reservations

router = APIRouter()


@router.post("/admin/stock-reservations/expire")
def expire_stock_reservations(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db_transactional),
):
    try:
        expired_count = expire_active_reservations(now=datetime.utcnow(), db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": {"expired_count": int(expired_count)}}
