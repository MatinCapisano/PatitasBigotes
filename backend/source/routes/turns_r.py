from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from source.dependencies.auth_d import get_current_user, get_current_user_id
from source.db.session import get_db
from source.errors import raise_http_error_from_exception
from source.schemas import CreateTurnRequest
from source.services.turns_s import create_turn_for_user

router = APIRouter()


@router.post("/turns")
def create_turn(
    payload: CreateTurnRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(current_user)
    try:
        turn = create_turn_for_user(
            user_id=user_id,
            scheduled_at=payload.scheduled_at,
            notes=payload.notes,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": turn}
